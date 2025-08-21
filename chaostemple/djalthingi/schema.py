from ninja import Schema


class ParliamentSchema(Schema):
    parliament_num: int


class IssueSchema(Schema):
    issue_num: int
    parliament: ParliamentSchema
    name: str


class DocumentSchema(Schema):
    doc_num: int
    doc_type: str
    html_content_path: str
    law_identifier: str
    html_remote_path: str
    issue: IssueSchema
