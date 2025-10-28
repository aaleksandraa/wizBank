from importlib import import_module

BANK_RULES = {
    # postojeći
    "homebank@nlb-rs.ba": "nlb_rs",
    "info.rbbh@rbbh.ba": "rbbh",
    "izvodi.pravne@unicreditgroup.ba": "unicredit",
    # novi
    "back.office@atosbank.ba": "atos",
    "izvodi@procreditbank.ba": "procredit",
    "izvodi@asabanka.ba": "asa",
    "izvodi.rs.ba@addiko.com": "addiko",
    "ziraatbankbh@bulk.ziraatbank.ba": "ziraat",
    "izvodi@sparkasse.ba": "sparkasse",
    "novabanka-eizvodi@novabanka.com": "nova",
}

def get_parser_by_sender(sender_email: str):
    if not sender_email:
        return import_module("wizvod.core.bank_rules.generic")
    s = sender_email.strip().lower()
    for key, module_name in BANK_RULES.items():
        if key.lower() in s:
            return import_module(f"wizvod.core.bank_rules.{module_name}")
    return import_module("wizvod.core.bank_rules.generic")

def extract_statement_number(sender_email: str, text: str):
    parser = get_parser_by_sender(sender_email)
    return getattr(parser, "extract_statement_number", lambda *_: None)(text)

def extract_account_number(sender_email: str, text: str, subject: str, filename: str):
    parser = get_parser_by_sender(sender_email)
    return getattr(parser, "extract_account_number", lambda *_: None)(text, subject, filename)
