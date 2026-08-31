"""替换流程编排服务：验证 → 解析 RTF → 映射 → 写 config.xml → 保存元数据

从 MainTab 中拆出的业务编排层。重活（解析/映射/写文件）仍放到线程池执行，
但通过 threading.Event 实现真正的取消：Cancel 置位后，映射循环内逐球员检查
并中断，后续阶段不再执行，config.xml 不会被写入。
"""
import asyncio
import os
import threading

import toga

from .core.FaceMapper import FaceMapper
from .core.RtfParser import RtfParser
from .core.XmlParser import XmlParser


class ReplaceFacesService:
    """Replace Faces 的执行控制器，支持线程级取消"""

    def __init__(self, app):
        self.app = app
        self.logger = app.logger
        # 取消标志：UI 线程置位，工作线程在各阶段检查
        self.cancel_event = threading.Event()
        # 供 UI（Viewer 预览等）读取的最近一次结果
        self.rtf_data = None
        self.mapping_data = None

    @property
    def cancelled(self):
        return self.cancel_event.is_set()

    def request_cancel(self):
        """请求取消当前正在执行的替换任务"""
        self.cancel_event.set()
        self.logger.info("Cancel requested by user")

    async def run(self, rtf, img_dir, profile, mode, filter_newgen,
                  allow_duplicates, save_backup, on_progress) -> str:
        """执行完整的替换流程

        Args:
            on_progress: 同步回调 on_progress(status: str, value: int)，用于更新 UI 进度

        Returns:
            str: "finished" | "cancelled" | "failed"
        """
        self.cancel_event = threading.Event()
        loop = asyncio.get_running_loop()
        try:
            # 步骤1: 验证RTF文件
            on_progress("Validating RTF file...", 0)
            rtf_parser = RtfParser()
            if not await self._validate_rtf_file(rtf, rtf_parser):
                return "failed"
            if self.cancelled:
                return "cancelled"
            # 步骤2: 验证图片目录
            on_progress("Validating image directory...", 10)
            if not await self._validate_image_directory(img_dir):
                return "failed"
            if self.cancelled:
                return "cancelled"
            # 步骤3: 解析RTF文件 (放到线程池中执行)
            on_progress("Parsing RTF file...", 20)
            self.rtf_data = await loop.run_in_executor(
                None, self._parse_rtf_file, rtf, rtf_parser, filter_newgan)
            if self.rtf_data is None:
                return "cancelled" if self.cancelled else "failed"
            # 步骤4: 生成映射数据 (放到线程池中执行，可被取消标志中断)
            on_progress("Mapping player to image...", 40)
            self.mapping_data = await loop.run_in_executor(
                None, self._generate_mapping_data,
                img_dir, self.rtf_data, mode, allow_duplicates)
            if self.mapping_data is None:
                return "cancelled" if self.cancelled else "failed"
            # 步骤5: 生成config.xml文件 (放到线程池中执行)
            on_progress("Generating config.xml...", 80)
            result = await loop.run_in_executor(
                None, self._generate_config_xml, self.mapping_data,
                img_dir, self.app.profile_manager.root_dir,
                self.app.profile_manager.logger, save_backup)
            if not result:
                return "cancelled" if self.cancelled else "failed"
            # 步骤6: 保存元数据
            on_progress("Saving profile metadata...", 90)
            await self._save_profile_metadata(profile)
            # 完成
            on_progress("Finished! :)", 100)
            return "finished"
        except Exception as e:
            self.logger.error(f"Error in replace faces task: {e}", exc_info=True)
            await self.app.throw_error(f"Error during face replacement: {e}")
            return "failed"

    async def _validate_rtf_file(self, rtf_path, rtf_parser):
        try:
            # 验证RTF文件格式
            if not rtf_parser.check_rtf_valid(rtf_path):
                await self.app.throw_error("The RTF file is invalid!")
                return False
        except FileNotFoundError:
            self.logger.error(f"RTF file doesn't exist: {rtf_path}")
            await self.app.throw_error("The RTF file doesn't exist!")
            return False
        except PermissionError:
            self.logger.error(f"Permission denied to access RTF file: {rtf_path}")
            await self.app.throw_error("Permission denied to access the RTF file!")
            return False
        except Exception as e:
            self.logger.error(f"Error while validating RTF file: {e}")
            await self.app.throw_error(f"Error while validating RTF file: {e}")
            return False
        return True

    async def _validate_image_directory(self, img_dir):
        if not os.path.isdir(img_dir):
            await self.app.throw_error("The image directory doesn't exist!")
            self.app.profile_manager.prf_cfg['img_dir'] = ''
            return False
        # 检查图像目录是否包含所有需要的子文件夹
        img_dirs = set()
        for entry in os.scandir(img_dir):
            if entry.is_dir():
                img_dirs.add(entry.name)
        for fp_dir in self.app.facepack_dirs:
            if fp_dir not in img_dirs:
                # 询问用户是否要创建缺失的目录
                self.logger.info(f"Folder '{fp_dir}' is missing in the image directory")
                dialog = toga.QuestionDialog("Missing Directory", f"Folder '{fp_dir}' is missing in the image directory. Do you want to create it and continue?")
                user_choose = await self.app.main_window.dialog(dialog)
                if user_choose:
                    try:
                        os.makedirs(os.path.join(img_dir, fp_dir), exist_ok=True)
                        self.logger.info(f"Created directory: {fp_dir}")
                        continue
                    except Exception as e:
                        await self.app.throw_error(f"Failed to create directory {fp_dir}: {e}")
                        return False
                else:
                    # 用户选择不创建目录，显示提示错误对话框并返回False
                    self.logger.error(f"Folder '{fp_dir}' is missing in the image directory, and user chose not to create it.")
                    await self.app.throw_error(f"Folder {fp_dir} is missing in the image directory")
                    return False
        return True

    def _parse_rtf_file(self, rtf_path, rtf_parser, filter_newgan):
        """解析RTF文件"""
        try:
            return rtf_parser.parse_rtf(rtf_path, filter_newgan)
        except FileNotFoundError:
            self.logger.error("RTF file not found")
        except UnicodeDecodeError:
            self.logger.error("Encoding error in RTF file")
        except Exception as e:
            self.logger.error(f"Error parsing RTF file: {e}")
        return None

    def _generate_mapping_data(self, img_dir, rtf_data, mode, allow_duplicates):
        """生成映射数据（映射循环内响应取消标志）"""
        try:
            return FaceMapper(img_dir, self.app.profile_manager).generate_mapping(
                rtf_data, mode, allow_duplicates, cancel_event=self.cancel_event
            )
        except Exception as e:
            self.logger.error(f"Error mapping player to image: {e}")
            return None

    def _generate_config_xml(self, mapping_data, img_dir, root_dir, logger, save_backup):
        """生成配置文件"""
        try:
            xml_parser = XmlParser()
            xml_parser.write_xml(mapping_data, img_dir, root_dir, logger, save_backup)
            return True
        except FileNotFoundError:
            self.logger.error("Config_template file not found")
        except Exception as e:
            self.logger.error(f"Error while writing XML: {e}")
        return False

    async def _save_profile_metadata(self, profile):
        """保存配置文件元数据"""
        try:
            self.app.profile_manager.save_config(
                self.app.profile_manager.user_path(profile + ".json"),
                self.app.profile_manager.prf_cfg
            )
            return True
        except Exception as e:
            self.logger.error(f"Error saving profile metadata: {e}")
            await self.app.throw_error(f"Error saving profile: {e}")
            return False
