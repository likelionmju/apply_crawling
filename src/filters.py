from threading import Thread
from queue import Queue


secrets = dict()


class AbstractFilter(Thread):

    def __init__(self, src_queue: Queue, snk_queue: Queue) -> None:
        super().__init__()
        self._src_queue = src_queue
        self._snk_queue = snk_queue

    def run(self) -> None:
        self.operate()

    def operate(self) -> None:
        pass


class InitFilter(AbstractFilter):

    def operate(self) -> None:
        import json
        org_param = self._src_queue.get()
        with open(org_param) as f:
            global secrets
            secrets = json.loads(f.read())
            new_param = {
                "admin_info": {"id": secrets["ADMIN_ID"], "password": secrets["ADMIN_PASSWORD"]},
                "univ_code": secrets["ADMIN_ID"].split("@")[0]
            }
            self._snk_queue.put(new_param)


class LoginFilter(AbstractFilter):

    def operate(self) -> None:
        from crawler import login
        org_param = self._src_queue.get()
        admin_info = org_param["admin_info"]
        data = {ck["name"]: ck["value"] for ck in login(admin_info["id"], admin_info["password"])}
        if data.get("sessionid") is None:
            return
        next_param = {
            "univ_code": org_param["univ_code"],
            "login_info": data
        }
        self._snk_queue.put(next_param)


class PreParseFilter(AbstractFilter):

    def operate(self) -> None:
        from crawler import request_univ_page_source, extract_all_applicant_pks
        org_param = self._src_queue.get()
        source = request_univ_page_source(org_param["univ_code"], org_param["login_info"])
        pks = extract_all_applicant_pks(source)
        new_param = [{"pk": pk, "login_info": org_param["login_info"]} for pk in pks]
        self._snk_queue.put(new_param)


class RequestApplicantPageFilter(AbstractFilter):

    def operate(self) -> None:
        from crawler import request_applicant_source
        org_param = self._src_queue.get()
        new_param = request_applicant_source(org_param["pk"], org_param["login_info"])
        self._snk_queue.put(new_param)


class ApplicantPageParseFilter(AbstractFilter):

    def operate(self) -> None:
        from crawler import parse_applicant_page
        org_param = self._src_queue.get()
        self._snk_queue.put(parse_applicant_page(org_param, 5))


class ExitFilter(AbstractFilter):

    def operate(self) -> None:
        from crawler import download_applicant_file, export_docx
        applicant = self._src_queue.get()
        download_applicant_file(applicant)
        export_docx(applicant)
