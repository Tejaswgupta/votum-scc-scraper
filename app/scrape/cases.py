from bs4 import BeautifulSoup


class CasesScrapper:
    def __init__(self, page: str):
        self.soup = BeautifulSoup(page, "lxml")

    def extract_scc_id(self):
        section_head_text = self.soup.find("div", class_="SectionheadText")
        scc_id = section_head_text.find("b")
        if scc_id:
            return scc_id.text

    def extract_bench_name(self):
        bench_name = self.soup.find("p", class_="j")
        if bench_name:
            return bench_name.text

    def extract_case_no(self):
        case_no = self.soup.find("p", class_="caseno")
        if case_no:
            return case_no.text

    def extract_advocates(self):
        advocates = self.soup.find_all("p", class_="advo")
        return [advocate.text for advocate in advocates if advocate]

    def extract_citation_links(self):
        citation_links = self.soup.find_all("a", class_="citalink")
        return list(set([link.get("onclick").split("'")[1] for link in citation_links if link]))