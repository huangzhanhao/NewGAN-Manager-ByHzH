import unittest
import sys
import os
from unittest.mock import Mock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'newganmanager'))

# 从core导入模块
from newganmanager.core.Mapper import Mapper
import shutil


class TestMapper(unittest.TestCase):
    """测试Mapper类"""

    def setUp(self):
        self.test_data_dir = os.path.join(os.path.dirname(__file__), "testing_data")
        shutil.copyfile(os.path.join(os.path.dirname(__file__), "..", "newganmanager", ".user", "default_cfg.json"),
                       os.path.join(self.test_data_dir, ".user", "cfg.json"))
        self.pm = Mock()
        self.mapper = Mapper(self.test_data_dir + "/", self.pm)
        
        # 设置测试用的民族映射
        ethnicities = ["African", "Asian", "EECA", "Italmed", "SAMed", "South American",
                      "SpanMed", "YugoGreek", "MENA", "MESA", "Caucasian", "Central European",
                      "Scandinavian", "Seasian"]
        for eth in ethnicities:
            self.mapper.eth_map[eth] = {f"{eth}{i}" for i in range(20)}

    def tearDown(self):
        test_data_dir = os.path.join(os.path.dirname(__file__), "testing_data")
        config_dir = os.path.join(test_data_dir, ".config")
        user_dir = os.path.join(test_data_dir, ".user")

        if os.path.exists(config_dir):
            shutil.rmtree(config_dir)
        shutil.copytree(os.path.join(os.path.dirname(__file__), "..", "newganmanager", ".config"), config_dir)

        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        shutil.copytree(os.path.join(os.path.dirname(__file__), "..", "newganmanager", ".user"), user_dir)

        config_xml_path = os.path.join(test_data_dir, "config.xml")
        with open(config_xml_path, "w") as cfg:
            cfg.write('OUTSIDE')

    def test_mapper_initialization(self):
        """测试Mapper初始化"""
        # 检查Mapper是否正确初始化属性
        self.assertEqual(self.mapper.img_dir, self.test_data_dir + "/")
        self.assertEqual(self.mapper.profile_manager, self.pm)
        
        # 检查eth_map是否正确构建
        self.assertIn("African", self.mapper.eth_map)
        self.assertIn("Asian", self.mapper.eth_map)

    def test_skin_color_mapping(self):
        """测试不同肤色代码的民族映射"""
        test_cases = [
            # (skin_color, first_nation, second_nation, expected_ethnicity)
            ("1", "ESP", "BAS", "SpanMed"),      # ESP->SpanMed
            ("1", "KSA", "ARG", "MESA"),         # KSA->MESA
            ("1", "ITA", "SMR", "Italmed"),      # ITA->Italmed
            ("0", "SWE", "", "Scandinavian"),    # Scandinavian special case
            ("0", "ENG", "", "Caucasian"),       # Caucasian special case
            ("2", "EGY", "KSA", "MESA"),         # MESA特殊情况
            ("2", "EGY", "IRQ", "MENA"),         # 默认MENA情况
            ("4", "KSA", "", "MESA"),            # MESA肤色4
            ("5", "THA", "", "Seasian"),         # Seasian肤色5
            ("10", "ARG", "", "South American"), # South American特殊处理
            ("10", "CHN", "", "Asian"),          # 默认亚洲处理
        ]
        
        for skin_color, first_nat, sec_nat, expected_ethnicity in test_cases:
            with self.subTest(skin_color=skin_color, first_nat=first_nat, sec_nat=sec_nat):
                def get_ethnic_side_effect(nation):
                    ethnic_map = {
                        "ESP": "SpanMed", "BAS": "SpanMed",
                        "KSA": "MESA", "ARG": "SAMed",
                        "ITA": "Italmed", "SMR": "Italmed",
                        "SWE": "Scandinavian",
                        "ENG": "Caucasian",
                        "EGY": "MENA", 
                        "IRQ": "MESA",
                        "THA": "Seasian",
                        "CHN": "Asian"
                    }
                    return ethnic_map.get(nation)
                
                self.pm.get_ethnic.side_effect = get_ethnic_side_effect
                
                # 模拟RTF数据: [UID, first_nat, sec_nat, eth_code]
                rtf_data = [["1234567890", first_nat, sec_nat, skin_color]]
                mapping = self.mapper.generate_mapping(rtf_data, "Generate")
                
                self.assertEqual(len(mapping), 1)
                self.assertEqual(mapping[0][1], expected_ethnicity)

    def test_african_skin_tones_mapping(self):
        """测试非洲肤色(3,6,7,8,9)的民族映射"""
        # 设置profile manager返回African民族
        self.pm.get_ethnic.return_value = "African"
        
        # 测试各种非洲肤色代码
        african_skin_tones = ["3", "6", "7", "8", "9"]
        for skin_tone in african_skin_tones:
            with self.subTest(skin_tone=skin_tone):
                # 模拟RTF数据: [UID, first_nat, sec_nat, eth_code]
                rtf_data = [["1234567890", "NGA", "", skin_tone]]
                mapping = self.mapper.generate_mapping(rtf_data, "Generate")
                
                self.assertEqual(len(mapping), 1)
                self.assertEqual(mapping[0][1], "African")

    def test_invalid_skin_tone_handling(self):
        """测试无效的肤色代码处理"""
        with patch.object(self.mapper, 'logger') as mock_logger:
            # 设置profile manager返回一个有效民族
            self.pm.get_ethnic.return_value = "Caucasian"
            
            # 模拟RTF数据: [UID, first_nat, sec_nat, eth_code]，其中eth_code为无效值11
            rtf_data = [["1234567890", "ENG", "", "11"]]
            mapping = self.mapper.generate_mapping(rtf_data, "Generate")
            
            # 应该跳过该球员，所以映射结果为空
            self.assertEqual(len(mapping), 0)
            
            # 应该记录日志
            mock_logger.info.assert_called_with(
                "Ethnic value {} is invalid. Most likely a bug in the view. Skipping player {}".format("11", "1234567890")
            )

    def test_missing_ethnic_mapping(self):
        """测试缺失民族映射的处理"""
        with patch.object(self.mapper, 'logger') as mock_logger:
            # 模拟profile manager无法找到民族映射
            self.pm.get_ethnic.return_value = None
            
            # 模拟RTF数据: [UID, first_nat, sec_nat, eth_code]
            rtf_data = [["1234567890", "XXX", "", "1"]]  # XXX是一个未知国家代码
            mapping = self.mapper.generate_mapping(rtf_data, "Generate")
            
            # 应该跳过该球员，所以映射结果为空
            self.assertEqual(len(mapping), 0)
            
            # 应该记录日志
            mock_logger.info.assert_called_with(
                "Mapping for {} is missing. Skipping player {}".format("XXX", "1234567890")
            )

    def test_generate_mode_basic(self):
        """测试Generate模式基本功能"""
        # 设置profile manager
        def get_ethnic_side_effect(nation):
            ethnic_map = {
                "ESP": "SpanMed",
                "KSA": "MESA"
            }
            return ethnic_map.get(nation)
        
        self.pm.get_ethnic.side_effect = get_ethnic_side_effect
        
        # 模拟RTF数据
        rtf_data = [
            ["1915714540", "ESP", "BAS", "1"],
            ["1915576430", "KSA", "ARG", "2"]
        ]
        
        mapping = self.mapper.generate_mapping(rtf_data, "Generate")
        
        # 检查映射结果
        self.assertEqual(len(mapping), 2)
        self.assertEqual(mapping[0][0], "1915714540")
        self.assertEqual(mapping[0][1], "SpanMed")
        self.assertEqual(mapping[1][0], "1915576430")
        self.assertEqual(mapping[1][1], "MESA")

    def test_preserve_mode_with_existing_data(self):
        """测试Preserve模式与现有数据的处理"""
        with patch('newganmanager.core.mapper.XmlParser') as mock_xml_parser:
            # 模拟已有的XML数据
            mock_xml_parser.return_value.parse_xml.return_value = {
                "1915714540": {"ethnicity": "SpanMed", "image": "SpanMed10"}
            }
            
            # 设置profile manager
            self.pm.get_ethnic.return_value = "MESA"
            
            # 模拟RTF数据，包含一个已存在的UID和一个新的UID
            rtf_data = [
                ["1915714540", "ESP", "BAS", "1"],  # 已存在的UID
                ["1915576430", "KSA", "ARG", "2"]   # 新的UID
            ]
            
            with patch.object(self.mapper, 'logger') as mock_logger:
                mapping = self.mapper.generate_mapping(rtf_data, "Preserve")
                
                # 检查结果：应该包含两个映射，一个是已存在的，一个是新的
                self.assertEqual(len(mapping), 2)
                
                # 检查已存在的UID是否被保留
                preserved_entry = next((m for m in mapping if m[0] == "1915714540"), None)
                self.assertIsNotNone(preserved_entry)
                self.assertEqual(preserved_entry[1], "SpanMed")
                self.assertEqual(preserved_entry[2], "SpanMed10")
                
                # 检查新的UID是否被映射
                new_entry = next((m for m in mapping if m[0] == "1915576430"), None)
                self.assertIsNotNone(new_entry)
                self.assertEqual(new_entry[1], "MESA")
                
                # 检查是否记录了保留的日志
                mock_logger.info.assert_any_call(
                    "Preserve: {} {} {}".format("1915714540", "SpanMed", "SpanMed10")
                )

    def test_overwrite_mode_with_existing_data(self):
        """测试Overwrite模式与现有数据的处理"""
        with patch('newganmanager.core.mapper.XmlParser') as mock_xml_parser:
            # 模拟已有的XML数据
            mock_xml_parser.return_value.parse_xml.return_value = {
                "1915714540": {"ethnicity": "SpanMed", "image": "SpanMed10"}
            }
            
            # 设置profile manager
            def get_ethnic_side_effect(nation):
                ethnic_map = {
                    "ESP": "SpanMed",
                    "KSA": "MESA"
                }
                return ethnic_map.get(nation)
            
            self.pm.get_ethnic.side_effect = get_ethnic_side_effect
            
            # 模拟RTF数据，包含一个已存在的UID和一个新的UID
            rtf_data = [
                ["1915714540", "ESP", "BAS", "1"],  # 已存在的UID
                ["1915576430", "KSA", "ARG", "2"]   # 新的UID
            ]
            
            mapping = self.mapper.generate_mapping(rtf_data, "Overwrite")
            
            # 检查结果：应该包含两个映射，已存在的被覆盖了，新的被添加
            self.assertEqual(len(mapping), 2)
            
            # 检查已存在的UID是否被重新映射（覆盖）
            overwritten_entry = next((m for m in mapping if m[0] == "1915714540"), None)
            self.assertIsNotNone(overwritten_entry)
            self.assertEqual(overwritten_entry[1], "SpanMed")
            
            # 检查新的UID是否被映射
            new_entry = next((m for m in mapping if m[0] == "1915576430"), None)
            self.assertIsNotNone(new_entry)
            self.assertEqual(new_entry[1], "MESA")

    def test_pick_image_from_available_pool(self):
        """测试从可用图像池中选择图像"""
        # 设置民族映射
        self.mapper.eth_map = {"African": {"African0", "African1", "African2"}}
        
        # 选择图像
        with patch('newganmanager.core.mapper.random') as mock_random:
            mock_random.choice.return_value = "African1"
            image = self.mapper.pick_image("African")
        
        # 检查返回的图像是否在集合中
        self.assertIn(image, {"African0", "African1", "African2"})

    def test_pick_image_without_duplicates(self):
        """测试不重复选择图像"""
        # 设置民族映射
        self.mapper.eth_map = {"African": {"African0", "African1", "African2"}}
        
        # 选择图像，不允许重复
        with patch('newganmanager.core.mapper.random') as mock_random:
            mock_random.choice.return_value = "African1"
            image = self.mapper.pick_image("African", duplicates=False)
        
        # 检查返回的图像是否正确
        self.assertEqual(image, "African1")
        # 检查图像是否从集合中移除
        self.assertNotIn("African1", self.mapper.eth_map["African"])

    def test_pick_image_from_empty_pool(self):
        """测试从空图像池中选择图像"""
        # 设置空的民族映射
        self.mapper.eth_map = {"African": set()}
        
        # 选择图像应该返回None
        image = self.mapper.pick_image("African")
        self.assertIsNone(image)

    def test_get_xml_images(self):
        """测试获取XML图像列表"""
        # 模拟XML数据
        xml_data = {
            "1234567890": {"ethnicity": "African", "image": "African0"},
            "0987654321": {"ethnicity": "Asian", "image": "Asian1"}
        }
        
        # 获取图像列表
        images = self.mapper.get_xml_images(xml_data)
        
        # 检查结果
        self.assertIn("African0", images)
        self.assertIn("Asian1", images)
        self.assertEqual(len(images), 2)

    def test_post_rtf_hook(self):
        """测试post_rtf_hook方法"""
        # 准备测试数据
        mapping = [["1234567890", "African", "African0"]]
        prf_imgs = ["African0"]
        xml_data = {
            "0987654321": {"ethnicity": "Asian", "image": "Asian1"}
        }
        
        # 调用post_rtf_hook
        self.mapper.post_rtf_hook(mapping, prf_imgs, xml_data)
        
        # 检查映射是否被更新
        self.assertEqual(len(mapping), 2)
        self.assertEqual(mapping[1], ["0987654321", "Asian", "Asian1"])

    def test_empty_rtf_data(self):
        """测试空的RTF数据"""
        self.pm.get_ethnic.return_value = "African"
        rtf_data = []
        mapping = self.mapper.generate_mapping(rtf_data, "Generate")
        self.assertEqual(mapping, [])

    def test_invalid_mode(self):
        """测试无效的映射模式"""
        self.pm.get_ethnic.return_value = "African"
        rtf_data = [["1234567890", "NGA", "", "3"]]
        
        # 使用无效模式应该仍然可以处理，只是不触发特定模式逻辑
        mapping = self.mapper.generate_mapping(rtf_data, "InvalidMode")
        self.assertEqual(len(mapping), 1)
        self.assertEqual(mapping[0][1], "African")


if __name__ == '__main__':
    unittest.main()
