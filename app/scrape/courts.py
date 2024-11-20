import threading
import time
from calendar import month
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

import psycopg2
import requests
from requests import Response

from app import constants
from app.custom_dataclasses import Court
from app.db.cases.crud import get_case_by_scc_id, get_cases_by_date, insert_case
from app.db.scraped.crud import insert_scraped_record
from app.logger import logger
from app.scrape.cases import CasesScrapper
from app.scrape.citations import CitationsAPI


class CourtsAPI:
    def __init__(self):
        self.citation_api = CitationsAPI()
        self.cases_executor = ThreadPoolExecutor(max_workers=100)
        self.citations_executor = ThreadPoolExecutor(max_workers=100)
        self.records = []
        self.record = {}

    def get_courts_recursively(self, aspxauth_container: dict):
        all_courts = {}
        countries = self.get_countries()

        for country in countries:
            courts_data = self._fetch_courts_and_subcourts(
                aspxauth_container, country, [country]
            )
            all_courts[country.key_formatted()] = courts_data

        return all_courts

    def _fetch_courts_and_subcourts(
        self, aspxauth_container: dict, country: str, previous_courts: list
    ) -> list:
        """
        Recursively retrieves court data from a hierarchical API structure, starting with a specified country and
        traversing its court hierarchy. The function builds and sends POST requests to the API using authentication
        from `aspxauth_container` and dynamically generated query parameters.

        - It constructs a payload that specifies the current depth in the court hierarchy (using `previous_courts`)
          and sends it to the API.
        - For each response, it processes the retrieved court data. If a court item represents a final (or "Title") level,
          additional data is fetched by calling `get_xml_path`, followed by `get_page_data` to retrieve the court's case page.
          Case information is then scraped and stored in the database.
        - If a court item has sub-levels, it recursively calls itself to explore further down the hierarchy,
          ensuring each level's court data is processed before unwinding the recursion.
        - The function aggregates data for all subcourts and ensures it's stored properly for each node in the hierarchy.
        """
        courts_scraped = []
        url = f"{constants.BASE_URL}/Searcher.svc/SearchBrowseTree"
        headers = self._get_headers(aspxauth_container["ASPXAUTH"])

        query_text = self._generate_query_text(previous_courts)
        data = {
            "searchDetails": {
                "QueryText": query_text,
                "ReturnOnExit": False,
                "RequiredRows": 500,
                "SelectedCourt": "",
                "HighlightTree": True,
                "IsIclrContent": True,
                "IsJudiciaryPackage": False,
                "SearchText": "",
                "IsMootCourtAccessible": "false",
                "CountryName": "india",
                "SearchType": "Judgments (Court Wise)",
                "IsBrowseBySearch": False,
                "SearchField": f"{previous_courts[-1].level}",  # Adjust the search field based on depth
                "User SubscribedAddonList": ["NoAddOn"],
                "QueryType": f"{previous_courts[-1].key}",
                "parentNode": f"{previous_courts[-2].level}"
                if len(previous_courts) > 1
                else "Node1",
                "HasChildren": True,
            }
        }

        try:
            # Send POST request to the API and validate the response.
            # The response represents the court data at the current level in the hierarchy
            # The response has two important fields for us: level and key
            # Where level is the type of court (e.g. "Year", "Month", "Title")
            # And key is the value of that level (e.g. "2021", "January", "Supreme Court")
            response = requests.post(url, headers=headers, json=data)
            if response.status_code == 200 and self._validate_court_response(
                response, country.level, "_fetch_courts_and_subcourts"
            ):
                courts_data = response.json().get("d")[0].get("children", [])
                for court_data in courts_data:
                    court = Court(
                        key=court_data.get("key"), level=court_data.get("level")
                    )
                    self.record[court.level] = court.key_formatted()

                    # 'Title' here is the final level of the court hierarchy
                    # If the court is at the final level, fetch additional data and store it in the database
                    if court.level == "Title":
                        xml = self.get_xml_path(
                            aspxauth_container, court.key_formatted()
                        )
                        page = self.get_page_data(aspxauth_container, xml)
                        self.record["page_xml"] = page

                        # 'case_info' is a dictionary containing information about the case
                        # Particulary: scc_id, bench_name, case_no, advocates, citations
                        case_info = self.scrap_case_information_from_case_page(page)

                        existing_case = get_case_by_scc_id(case_info.get("scc_id"))
                        if existing_case:
                            continue

                        case_id = self.save_case_into_db(
                            case_info=case_info, record=self.record
                        )

                        # For each citation in the case, scrap additional data and store it in the database
                        self.citations_executor.submit(
                            self._process_citations,
                            aspxauth_container,
                            case_info.get("citations"),
                            case_id,
                        )

                        # Store the record in the database
                        # It is just for justification that the record was scraped
                        insert_scraped_record(
                            court_type=country.key,
                            court_name=self.record.get("Node3"),
                            year=int(self.record.get("Year")),
                            month=int(self.record.get("Month")),
                            day=int(self.record.get("Date")),
                            completed=True,
                        )

                        self.records.append(self.record.copy())
                    else:
                        self.cases_executor.submit(
                            self._fetch_courts_and_subcourts,
                            aspxauth_container,
                            country,
                            previous_courts + [court],
                        )

        except Exception as e:
            logger.error(
                {
                    "message": "Error fetching courts and subcourts",
                    "exception": str(e),
                    "location": "_fetch_courts_and_subcourts",
                }
            )
            time.sleep(0.5)

        return courts_scraped

    def _get_headers(self, aspxauth: str) -> dict:
        return {
            "Host": "www.scconline.com",
            "Cookie": aspxauth,
            "Sec-Ch-Ua": '"Chromium";v="123", "Not:A-Brand";v="8"',
            "Sec-Ch-Ua-Mobile": "?0",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.122 Safari/537.36",
            "Content-Type": "application/json; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Request-Id": "|b9+GB.eAlTH",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Origin": "https://www.scconline.com",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.scconline.com/Members/BrowseResult.aspx",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Priority": "u=4, i",
        }

    def _generate_query_text(self, courts: list[Court]) -> str:
        formatted_nodes = []

        for court in courts:
            node_string = f'{court.level}:"{court.key_formatted()}"'
            formatted_nodes.append(node_string)

        formatted_nodes.reverse()
        return " AND ".join(formatted_nodes)

    def _validate_court_response(
        self, response: Response, searched_country: str, func: str
    ) -> bool:
        """
        Validates SCC API response for certain searched court.

        :param response: is a simple 'requests' response.
        :param searched_country: the name explain itself, needed for more robust logging.
        :param func: name of function where validation is called. this one is needed to log where some of the validation errors occur.
        :return: boolean that says either the court is valid or not
        """

        if not response.json().get("d"):
            logger.error(
                {
                    "message": f"key 'd' not found for courts of country {searched_country}",
                    "location": func,
                }
            )
            return False

        elif (
            not isinstance(response.json().get("d"), list)
            or len(response.json().get("d")) < 1
        ):
            logger.error(
                {
                    "message": f"key 'd' has empty result for {searched_country}",
                    "location": func,
                }
            )
            return False

        elif not response.json().get("d")[0].get("children"):
            logger.error(
                {
                    "message": f"no children found for court {response.json().get('d')[0]}",
                    "location": func,
                }
            )
            return False

        else:
            return True

    def _check_if_day_was_scraped(
        self, aspxauth_container: dict, country: str, previous_courts: list
    ) -> bool:
        url = f"{constants.BASE_URL}/Searcher.svc/SearchBrowseTree"
        headers = self._get_headers(aspxauth_container["ASPXAUTH"])

        query_text = self._generate_query_text(previous_courts)
        data = {
            "searchDetails": {
                "QueryText": query_text,
                "ReturnOnExit": False,
                "RequiredRows": 500,
                "SelectedCourt": "",
                "HighlightTree": True,
                "IsIclrContent": True,
                "IsJudiciaryPackage": False,
                "SearchText": "",
                "IsMootCourtAccessible": "false",
                "CountryName": "india",
                "SearchType": "Judgments (Court Wise)",
                "IsBrowseBySearch": False,
                "SearchField": f"{previous_courts[-1].level}",  # Adjust the search field based on depth
                "User SubscribedAddonList": ["NoAddOn"],
                "QueryType": f"{previous_courts[-1].key}",
                "parentNode": f"{previous_courts[-2].level}"
                if len(previous_courts) > 1
                else "Node1",
                "HasChildren": True,
            }
        }

        year, month, day = (
            self.record.get("Year"),
            self.record.get("Month"),
            self.record.get("Date"),
        )

        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200 and self._validate_court_response(
            response, country.level, "_check_if_day_was_scraped"
        ):
            response_titles = [
                children.get("title")
                for children in response.json().get("d")[0].get("children", [])
            ]

            date = datetime.strptime(f"{year}-{month}-{day}", "%Y-%m-%d").date()
            database_titles = [
                case.case_name for case in get_cases_by_date(date) if case
            ]

            if sorted(response_titles) == sorted(database_titles):
                return True
            else:
                return False

    def _form_record(self, court: dict) -> dict:
        record = {court.get("level"): court.get("key").split("$")[0]}
        for subcourt in court.get("subcourts", []):
            record[subcourt.level] = subcourt.key_formatted()
        return record

    def get_countries(self) -> list[Court]:
        return [
            Court(key="  India", level="Node2"),
            Court(key="International", level="Node2"),
        ]

    def get_xml_path(self, aspxauth_container, title):
        url = f"{constants.BASE_URL}/Searcher.svc/SearchRelativePath"
        headers = self._get_headers(aspxauth_container["ASPXAUTH"])

        data = {
            "searchDetails": {
                "QueryText": f'Title:"{title}"',
                "ReturnOnExit": False,
                "RequiredRows": 500,
                "SelectedCourt": "",
                "HighlightTree": True,
                "IsIclrContent": True,
                "IsJudiciaryPackage": False,
                "SearchText": "",
                "IsMootCourtAccessible": "false",
                "CountryName": "india",
                "SearchType": "Judgments (Court Wise)",
                "IsBrowseBySearch": False,
                "SearchField": "",
                "UserSubscribedAddonList": ["NoAddOn"],
                "QueryType": "",
                "parentNode": "Month",
                "HasChildren": False,
            }
        }

        while True:
            try:
                response = requests.post(url, headers=headers, json=data)
                return response.json().get("d")
            except Exception as e:
                time.sleep(0.5)
                logger.error(
                    {
                        "message": "Error while getting XML Path for title. Retrying...",
                        "exception": e,
                        "location": "CourtAPI.get_xml_path",
                    }
                )

    def get_page_data(self, aspxauth_container, xml_path):
        url = f"{constants.BASE_URL}/HelperServices/ServicesForCourtFunctionality.asmx/GetPageData"
        headers = self._get_headers(aspxauth_container["ASPXAUTH"])

        data = {
            "searchDetails": {
                "QueryText": f'"{xml_path}"',
                "SearchField": "RelativePath",
                "SelectedCourt": "",
                "QueryType": "browse",
                "SearchInResultQuery": [],
                "SearchFeature": "gSearch",
                "UserName": "ca2a23b9cbbcaa08009d889dfc725559",
            },
            "path": f"{xml_path}",
            "subheadingOrCitation": "",
            "isHighlight": False,
            "valueForXslt": "",
            "sectionSearchingForXslt": "",
            "DisplayNameFromTree": "",
        }

        while True:
            try:
                response = requests.post(url, headers=headers, json=data)
                return response.json().get("d")
            except Exception as e:
                time.sleep(0.5)
                logger.error(
                    {
                        "message": "Error while getting page data. Retrying...",
                        "exception": e,
                        "location": "CourtAPI.get_page_data",
                    }
                )

    def save_case_into_db(self, case_info: dict, record: dict):
        record = record.copy()
        record.update(case_info)

        if not isinstance(record, dict):
            logger.error(
                {
                    "message": "Record is not a dictionary",
                    "location": "save_record_into_db",
                }
            )
            return

        date = (
            datetime.strptime(
                f"{record.get('Year')}-{record.get('Month')}-{record.get('Date')}",
                "%Y-%m-%d",
            ).date(),
        )
        case_id = insert_case(
            scc_id=record.get("scc_id"),
            bench_name=record.get("bench_name"),
            court_name=record.get("Node3"),
            case_name=record.get("Title"),
            case_no=record.get("case_no"),
            date=date,
            advocates=record.get("advocates"),
            citations=record.get("citations"),
            case_text=record.get("page_xml"),
        )
        return case_id

    def scrap_case_information_from_case_page(self, page: str):
        spider = CasesScrapper(page)
        scc_id = spider.extract_scc_id()
        bench_name = spider.extract_bench_name()
        case_no = spider.extract_case_no()
        advocates = spider.extract_advocates()
        citations = spider.extract_citation_links()

        return {
            "scc_id": scc_id,
            "bench_name": bench_name,
            "case_no": case_no,
            "advocates": advocates,
            "citations": citations,
        }

    def _process_citations(
        self, aspxauth_container: dict, citations: list[str], case_id: int
    ):
        for citation_id in citations:
            self.citation_api.proccess_citation(
                aspxauth_container, citation_id, case_id
            )
