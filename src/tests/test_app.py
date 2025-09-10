import unittest
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'newganmanager'))

# 从core导入模块
from core.rtfparser import RTF_Parser
from core.config_manager import Config_Manager
from core.profile_manager import Profile_Manager
from core.xmlparser import XML_Parser
from core.reporter import Reporter
import shutil


class Test_Reporter(unittest.TestCase):
    def test_send_report(self):
        # TODO:
        pass

class Test_XML_Parser(unittest.TestCase):
    def test_parse_xml(self):
        # 修复文件路径
        test_file_path = os.path.join(os.path.dirname(__file__), "..", "testing_data", "tests.xml")
        test_xml = XML_Parser().parse_xml(test_file_path)
        self.assertDictEqual(test_xml, {"0123456789": {"ethnicity": "African", "image": "African1"}})

    def test_parse_xml_new_format(self):
        # 修复文件路径
        test_file_path = os.path.join(os.path.dirname(__file__), "..", "testing_data", "test_new_format.xml")
        test_xml = XML_Parser().parse_xml(test_file_path)
        expected = {
            "1234567": {"ethnicity": "African", "image": "African1"},
            "2345678": {"ethnicity": "African", "image": "African2"},
            "3456789": {"ethnicity": "Caucasian", "image": "Caucasian1"},
            "4567890": {"ethnicity": "Caucasian", "image": "Caucasian2"},
            "5678": {"ethnicity": "MESA", "image": "MESA1"},
            "6789": {"ethnicity": "MESA", "image": "MESA2"}
        }
        self.assertDictEqual(test_xml, expected)

    def test_get_imgpath_from_uid(self):
        # 修复文件路径
        test_file_path = os.path.join(os.path.dirname(__file__), "..", "testing_data", "tests.xml")
        test_img = XML_Parser().get_imgpath_from_uid(test_file_path, '0123456789')
        self.assertEqual(test_img, "African/African1")

    def test_get_imgpath_from_uid_negative(self):
        # 修复文件路径
        test_file_path = os.path.join(os.path.dirname(__file__), "..", "testing_data", "tests.xml")
        test_img = XML_Parser().get_imgpath_from_uid(test_file_path, '0000000000')
        self.assertIsNone(test_img)

class Test_RTF_Parser(unittest.TestCase):
    def test_parse_rtf(self):
        test_simple = RTF_Parser().parse_rtf("testing_data/test_simple.rtf")
        self.assertSequenceEqual(test_simple[0], ["1915714540", "ESP", "BAS", "1"])
        self.assertSequenceEqual(test_simple[1], ["1915576430", "KSA", "ARG", "2"])
        self.assertEqual(len(test_simple), 2)

    def test_parse_rtf_with_short_UIDs(self):
        test_simple_UID = RTF_Parser().parse_rtf("testing_data/test_simple_UID.rtf")
        self.assertSequenceEqual(test_simple_UID[0], ["1915576430", "KSA", "ARG", "2"])
        self.assertEqual(len(test_simple_UID), 1)

    def test_parse_rtf_fake_players(self):
        test_simple_UID_fake = RTF_Parser().parse_rtf("testing_data/test_simple_UID_fake.rtf")
        self.assertSequenceEqual(test_simple_UID_fake[0], ["1915576430", "KSA", "ARG", "2"])
        self.assertSequenceEqual(test_simple_UID_fake[1], ["1915576", "KSA", "GER", "2"])
        self.assertEqual(len(test_simple_UID_fake), 2)

    def test_valid_rtf(self):
        self.assertTrue(RTF_Parser().is_rtf_valid("testing_data/test_simple_UID.rtf"))
        self.assertFalse(RTF_Parser().is_rtf_valid("testing_data/false.rtf"))


class Test_Config_Manager(unittest.TestCase):

    def test_get_latest_prf(self):
        latest_prf = Config_Manager().get_latest_prf("testing_data/simple_cfg.json")
        self.assertEqual(latest_prf, "Profile2")


class Test_Xml_Writing(unittest.TestCase):
    def setUp(self):
        shutil.copyfile("../newganmanager/.user/default_cfg.json", "testing_data/.user/cfg.json")
        self.pm = Profile_Manager("No Profile", "testing_data")
        self.pm.prf_cfg["img_dir"] = "newganmanager/tests/"
        self.data = [
            ["African", "African1", "1915714540"],
            ["Caucasian", "Caucasian2", "1915576430"]
        ]
        self.xml_data = self.pm.write_xml(self.data)

    def test_write_xml_template_string_formatting(self):
        for xml_player, player in zip(self.xml_data, self.data):
            self.assertEqual("<record from=\""+player[1]+"/"+player[2]+"\" to=\"graphics/pictures/person/r-"+player[0]+"/portrait\"/>", xml_player)

    def test_write_xml_players_mapped_in_file(self):
        with open(self.pm.prf_cfg['img_dir']+"config.xml", 'r', encoding="UTF-8") as fp:
            xml_file = fp.read()
        for player in self.data:
            self.assertIn("<record from=\""+player[1]+"/"+player[2]+"\" to=\"graphics/pictures/person/r-"+player[0]+"/portrait\"/>", xml_file)

    def test_write_xml_no_file_endings(self):
        with open(self.pm.prf_cfg['img_dir']+"config.xml", 'r', encoding="UTF-8") as fp:
            xml_file = fp.read()
        self.assertNotIn(".png", xml_file)

    def tearDown(self):
        shutil.rmtree("testing_data/.config/")
        shutil.copytree("../newganmanager/.config/", "testing_data/.config/")
        shutil.rmtree("testing_data/.user/")
        shutil.copytree("../newganmanager/.user/", "testing_data/.user/")
        with open("testing_data/config.xml", "w") as cfg:
            cfg.write('OUTSIDE')


class Test_Profile_Manager(unittest.TestCase):
    def setUp(self):
        shutil.copyfile("../newganmanager/.user/default_cfg.json", "testing_data/.user/cfg.json")
        self.pm = Profile_Manager("No Profile", "testing_data")

    def test_delete_profile(self):
        cfg = Config_Manager().load_config("testing_data/.user/eth_cfg.json")
        cfg["Profile"] = {"testmig" : False, "No Profile": True}
        Config_Manager().save_config("testing_data/.user/cfg.json", cfg)
        f = open("testing_data/.user/testmig.xml", "a")
        f.write("TESTMIGXML!")
        f.close()
        f = open("testing_data/.user/testmig.json", "a")
        f.write("{'text': 'TESTMIGJSON!'}")
        f.close()
        self.pm.config = Config_Manager().load_config("testing_data/.user/cfg.json")
        self.pm.delete_profile("testmig")
        usr_cfg = Config_Manager().load_config("testing_data/.user/cfg.json")
        self.assertNotIn("testmig", usr_cfg["Profile"])
        self.assertIn("No Profile", usr_cfg["Profile"])
        self.assertFalse(os.path.isfile("testing_data/.user/testmig.json"))
        self.assertFalse(os.path.isfile("testing_data/.user/testmig.xml"))

    def test_create_profile(self):
        self.pm.create_profile("tests")
        cfg = Config_Manager().load_config("testing_data/.user/cfg.json")
        self.assertFalse(cfg["Profile"]["tests"])
        self.assertTrue(os.path.isfile("testing_data/.user/tests.json"))
        self.assertTrue(os.path.isfile("testing_data/.user/tests.xml"))
        prf_cfg = Config_Manager().load_config("testing_data/.user/tests.json")
        self.assertEqual(prf_cfg["imgs"], {})
        self.assertEqual(prf_cfg["ethnics"], {})
        self.assertEqual(prf_cfg["img_dir"], "")
        self.assertEqual(prf_cfg["rtf"], "")

    def test_load_profile(self):
        cfg = Config_Manager().load_config("testing_data/.user/cfg.json")
        cfg["Profile"] = {"testmig" : False, "No Profile": True}
        Config_Manager().save_config("testing_data/.user/cfg.json", cfg)
        f = open("testing_data/.user/testmig.xml", "a")
        f.write("TESTMIGXML!")
        f.close()
        f = open("testing_data/.user/testmig.json", "a")
        f.write("{\"img_dir\": \"newganmanager/tests/\"}")
        f.close()
        self.pm.config = cfg
        self.pm.root_dir = "testing_data"
        self.pm.load_profile("testmig")
        self.assertEqual(self.pm.cur_prf, "testmig")
        self.assertEqual(self.pm.prf_cfg["img_dir"], "newganmanager/tests/")
        with open("testing_data/config.xml", "r") as cfg_xml:
            data = cfg_xml.read()
            self.assertEqual(data, "TESTMIGXML!")
        self.assertTrue(self.pm.config["Profile"]["testmig"])
        self.assertFalse(self.pm.config["Profile"]["No Profile"])

    def test_swap_xml(self):
        self.pm.swap_xml("tests", "No Profile", "newganmanager/tests/", "newganmanager/tests/")
        with open("testing_data/.user/tests.xml", "r") as test_xml:
            self.assertEqual(test_xml.read(), "OUTSIDE")
        with open("testing_data/config.xml", "r") as config_xml:
            self.assertEqual(config_xml.read(), "")

    def test_get_ethnic(self):
        self.assertEqual(self.pm.get_ethnic("GER"), "Central European")
        self.assertEqual(self.pm.get_ethnic("ZZZ"), None)

    def test_switching_profiles_with_invalid_path(self):
        self.pm.swap_xml("tests", "No Profile", "newganmanager/invalid/", "newganmanager/tests/")
        self.pm.swap_xml("No Profile", "tests", "newganmanager/tests/", "newganmanager/invalid/")

    def test_migrate_function(self):
        shutil.copytree("../newganmanager/.config/", "../.config/")
        shutil.copy("../newganmanager/.user/No Profile.json", "../.config/No Profile.json")
        shutil.copy("../newganmanager/.user/No Profile.xml", "../.config/No Profile.xml")
        cfg = Config_Manager().load_config("../.config/eth_cfg.json")
        cfg["Profile"] = {"testmig" : False, "No Profile": True}
        Config_Manager().save_config("../.config/eth_cfg.json", cfg)
        f = open("../.config/testmig.xml", "a")
        f.write("TESTMIGXML!")
        f.close()
        f = open("../.config/testmig.json", "a")
        f.write("{'text': 'TESTMIGJSON!'}")
        f.close()
        self.pm.migrate_config()
        res_cfg = Config_Manager().load_config("testing_data/.config/eth_cfg.json")
        self.assertNotIn("Profile", res_cfg)
        self.assertIn("Ethnics", res_cfg)
        usr_cfg = Config_Manager().load_config("testing_data/.user/cfg.json")
        self.assertNotIn("Ethnics", usr_cfg)
        self.assertIn("Profile", usr_cfg)
        self.assertTrue(os.path.isfile("testing_data/.user/testmig.json"))
        self.assertTrue(os.path.isfile("testing_data/.user/testmig.xml"))
        self.assertFalse(os.path.isfile("../.config/testmig.json"))
        self.assertFalse(os.path.isfile("../.config/testmig.xml"))
        self.assertFalse(os.path.isdir("../.config"))

    def tearDown(self):
        shutil.rmtree("testing_data/.config/")
        shutil.copytree("../newganmanager/.config/", "testing_data/.config/")
        shutil.rmtree("testing_data/.user/")
        shutil.copytree("../newganmanager/.user/", "testing_data/.user/")
        with open("testing_data/config.xml", "w") as cfg:
            cfg.write('OUTSIDE')


if __name__ == '__main__':
    unittest.main()