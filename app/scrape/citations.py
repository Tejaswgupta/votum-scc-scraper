import re
import time
import requests
from bs4 import BeautifulSoup

from app import constants
from app.db.citations.crud import insert_citation
from app.logger import logger



class CitationsAPI:

    def proccess_citation(self, aspxauth_container: dict, citation_id: str, case_id: int):
        citation_type = 'STATUE' if 'JTXT' in citation_id else 'PRECEDENT'
        citation_data = self._get_citation_data(aspxauth_container, citation_id, citation_type)
        citation_path = self._get_citation_path(citation_data)
        citation_text = self._get_text_from_citation(aspxauth_container, citation_id, citation_path)

        soup = BeautifulSoup(citation_text, 'lxml')
        citation_title = soup.find(class_="SectionheadText")

        if citation_title:
            citation_title = citation_title.text
        else:
            citation_title = None

        print('case_id',type(case_id), case_id, )

        citation = insert_citation(
            unique_id=citation_id,
            case_id=case_id,
            title=citation_title,
            text=soup.prettify(),
            type=citation_type,
        )

        return citation

    def _get_citation_data(self, aspxauth_container: dict, citation_id: str, citation_type: str):
        url = f"{constants.BASE_URL}/Searcher.svc/SearchForCitaView"
        headers = self._get_headers(aspxauth_container)
        data = {
            "searchDetails": {
                "SearchField": 'DOI' if citation_type == 'STATUE' else '',
                "QueryText": f"{citation_id}",
                "RequiredRows": 50,
                "BuildTree": False,
                "QueryType": "Phrase",
                "SearchFeature": "browseresult",
                "SelectedCourt": "0000001111111111100001100100000000110000011111111000111111000001000100101000000000000000000000000000011101111111111111110110011101111111001100000000001111110100110111111111111111000111111111011111111110001111101110011111001011011111",
                "IsIclrContent": True,
                "packageGroupId": "1",
                "IsMootCourtAccessible": "false",
            }
        }

        while True:
            try:
                response = requests.post(url, headers=headers, json=data)
                return response.json()['d']
            except Exception as e:
                logger.error({
                    "message": "Error while getting citation data.",
                    "citation": citation_id,
                    "exception": str(e),
                    "location": "get_citation_data",
                })
                time.sleep(0.5)
                pass

    def _get_citation_path(self, citation_data: str):
        match = re.search(r'"Path":"(.*?)\.xml"', citation_data)
        if match:
            return match.group(1).replace("\\\\", "\\") + ".xml"

    def _get_text_from_citation(self, aspxauth_container, citation_id, path):
        url = f"{constants.BASE_URL}/HelperServices/ServicesForCourtFunctionality.asmx/GetPageData"
        headers = self._get_headers(aspxauth_container)
        data = {
            "searchDetails": {
                "QueryText": f"{citation_id}",
                "SearchField": "",
                "SelectedCourt": "",
                "QueryType": "Phrase",
                "SearchInResultQuery": [],
                "SearchWithSynStem": False,
                "UserName": "ca2a23b9cbbcaa08009d889dfc725559",
                "SearchFeature": "",
                "DOIForHighlight": "",
                "StatuesReference": "false",
            },
            "path": f"{path}",
            "subheadingOrCitation": "",
            "isHighlight": False,
            "valueForXslt": "",
            "sectionSearchingForXslt": "",
            "DisplayNameFromTree": "",
        }

        while True:
            try:
                response = requests.post(url, headers=headers, json=data)
                return response.json()['d']
            except Exception as e:
                logger.error({
                    "message": "Error while getting text from citation.",
                    "id": id,
                    "path": path,
                    "exception": str(e),
                    "location": "get_text_from_citation",
                })
                time.sleep(0.5)
                pass


    def _get_headers(self, aspxauth_container: dict) -> dict:
        return {
            "Cookie": aspxauth_container.get("ASPXAUTH"),
            "Content-Type": "application/json; charset=UTF-8",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Dest": "empty",
            "Referer": "https://www.scconline.com/Members/NoteView.aspx?enc=SlRYVC0wMDAyODk3ODYxJiYmJiY0MCYmJiYmQnJvd3NlUGFnZQ==",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.118 Safari/537.36",
            "Origin": "https://www.scconline.com",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Ch-Ua": '"Not-A.Brand";v="99", "Chromium";v="124"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "en-US,en;q=0.9",
            "Priority": "u=1, i",
        }
