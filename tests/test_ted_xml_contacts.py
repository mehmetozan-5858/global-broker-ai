import unittest

from src.ted_xml_parser import extract_ted_contacts


class TedXmlContactTests(unittest.TestCase):
    def test_extracts_explicit_touchpoint_fields(self):
        xml = b'''<?xml version="1.0" encoding="UTF-8"?>
        <Notice xmlns:cbc="urn:test">
          <TenderingParty>
            <Contact>
              <cbc:ContactName>Jane Buyer</cbc:ContactName>
              <cbc:ElectronicMail>procurement@example.eu</cbc:ElectronicMail>
              <cbc:Telephone>+32 2 555 12 34</cbc:Telephone>
              <cbc:InternetAddress>https://buyer.example.eu/procurement</cbc:InternetAddress>
            </Contact>
          </TenderingParty>
        </Notice>'''
        contact = extract_ted_contacts(xml)
        self.assertEqual(contact["contact_email"], "procurement@example.eu")
        self.assertEqual(contact["contact_phone"], "+32 2 555 12 34")
        self.assertEqual(contact["contact_person"], "Jane Buyer")
        self.assertEqual(contact["buyer_website"], "https://buyer.example.eu/procurement")
        self.assertEqual(contact["contact_evidence_source"], "ted_xml_touchpoint")

    def test_does_not_treat_unrelated_email_text_as_touchpoint(self):
        xml = b'''<?xml version="1.0"?><Notice><Description>
        Send product questions to random@example.com only as narrative text.
        </Description></Notice>'''
        self.assertNotIn("contact_email", extract_ted_contacts(xml))


if __name__ == "__main__":
    unittest.main()
