import unittest
import os
import sys

# Add the core directory to the path so we can import xmlparser
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'newganmanager', 'core'))

from xmlparser import XML_Parser


class TestXMLParser(unittest.TestCase):
    
    def setUp(self):
        self.parser = XML_Parser()
        
    def test_parse_xml_with_standard_uid(self):
        """
        Test parsing XML with standard UID format (7+ digits)
        """
        test_xml_content = '''<record>
        <list id="maps">
            <record from="African/African1" to="graphics/pictures/person/1234567/portrait"/>
        </list>
</record>'''
        
        # Create a temporary tests file
        with open('temp_test.xml', 'w', encoding='utf-8') as f:
            f.write(test_xml_content)
            
        result = self.parser.parse_xml('temp_test.xml')
        expected = {"1234567": {"ethnicity": "African", "image": "African1"}}
        self.assertDictEqual(result, expected)
        
        # Clean up
        os.remove('temp_test.xml')
        
    def test_parse_xml_with_r_prefix(self):
        """
        Test parsing XML with r- prefix in UID
        """
        test_xml_content = '''<record>
        <list id="maps">
            <record from="Caucasian/Caucasian1" to="graphics/pictures/person/r-2345678/portrait"/>
        </list>
</record>'''
        
        # Create a temporary tests file
        with open('temp_test.xml', 'w', encoding='utf-8') as f:
            f.write(test_xml_content)
            
        result = self.parser.parse_xml('temp_test.xml')
        expected = {"2345678": {"ethnicity": "Caucasian", "image": "Caucasian1"}}
        self.assertDictEqual(result, expected)
        
        # Clean up
        os.remove('temp_test.xml')
        
    def test_parse_xml_with_short_uid(self):
        """
        Test parsing XML with short UID (4-6 digits) - should be captured
        """
        test_xml_content = '''<record>
        <list id="maps">
            <record from="MESA/MESA1" to="graphics/pictures/person/5678/portrait"/>
        </list>
</record>'''
        
        # Create a temporary tests file
        with open('temp_test.xml', 'w', encoding='utf-8') as f:
            f.write(test_xml_content)
            
        result = self.parser.parse_xml('temp_test.xml')
        expected = {"5678": {"ethnicity": "MESA", "image": "MESA1"}}
        self.assertDictEqual(result, expected)
        
        # Clean up
        os.remove('temp_test.xml')
        
    def test_parse_xml_with_r_prefix_short_uid(self):
        """
        Test parsing XML with r- prefix and short UID
        """
        test_xml_content = '''<record>
        <list id="maps">
            <record from="EECA/EECA1" to="graphics/pictures/person/r-6789/portrait"/>
        </list>
</record>'''
        
        # Create a temporary tests file
        with open('temp_test.xml', 'w', encoding='utf-8') as f:
            f.write(test_xml_content)
            
        result = self.parser.parse_xml('temp_test.xml')
        expected = {"6789": {"ethnicity": "EECA", "image": "EECA1"}}
        self.assertDictEqual(result, expected)
        
        # Clean up
        os.remove('temp_test.xml')
        
    def test_parse_xml_multiple_entries(self):
        """
        Test parsing XML with multiple entries
        """
        test_xml_content = '''<record>
        <list id="maps">
            <record from="African/African1" to="graphics/pictures/person/1234567/portrait"/>
            <record from="Caucasian/Caucasian1" to="graphics/pictures/person/r-2345678/portrait"/>
            <record from="MESA/MESA1" to="graphics/pictures/person/5678/portrait"/>
        </list>
</record>'''
        
        # Create a temporary tests file
        with open('temp_test.xml', 'w', encoding='utf-8') as f:
            f.write(test_xml_content)
            
        result = self.parser.parse_xml('temp_test.xml')
        expected = {
            "1234567": {"ethnicity": "African", "image": "African1"},
            "2345678": {"ethnicity": "Caucasian", "image": "Caucasian1"},
            "5678": {"ethnicity": "MESA", "image": "MESA1"}
        }
        self.assertDictEqual(result, expected)
        
        # Clean up
        os.remove('temp_test.xml')
        
    def test_parse_xml_ignore_invalid_uids(self):
        """
        Test that invalid UIDs (less than 4 digits) are ignored
        """
        test_xml_content = '''<record>
        <list id="maps">
            <record from="Invalid/Invalid1" to="graphics/pictures/person/123/portrait"/>
            <record from="African/African1" to="graphics/pictures/person/1234567/portrait"/>
        </list>
</record>'''
        
        # Create a temporary tests file
        with open('temp_test.xml', 'w', encoding='utf-8') as f:
            f.write(test_xml_content)
            
        result = self.parser.parse_xml('temp_test.xml')
        # Should only capture the valid UID
        expected = {"1234567": {"ethnicity": "African", "image": "African1"}}
        self.assertDictEqual(result, expected)
        
        # Clean up
        os.remove('temp_test.xml')


if __name__ == '__main__':
    unittest.main()