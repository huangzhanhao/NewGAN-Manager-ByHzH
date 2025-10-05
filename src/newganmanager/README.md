# NewGAN Manager Project Overview

## Class Structure and Internal Methods

### Core Modules

#### ConfigManager
- `load_config(path)`
- `save_config(path, data)`
- `get_latest_prf(path)`

#### ProfileManager
- `migrate_config()`
- `delete_profile(name)`
- `create_profile(name)`
- `load_profile(name)`
- `write_xml(data, backup=True)`
- `swap_xml(deact_name, act_name, deact_img_dir, act_img_dir)`
- `get_ethnic(nation)`

#### RtfParser
- `parse_rtf(path)`
- `check_rtf_valid(path)`
- `translate_rtf_data_to_english(rtf_data)`

#### FaceMapper
- `generate_mapping(rtf_data, mode, duplicates=False)`
- `correct_ethnic(player, temp_eth1, temp_eth2)`
- `_process_preserve_mode(rtf_data, xml_data, duplicates)`
- `_process_overwrite_mode(rtf_data, xml_data, duplicates)`
- `_process_generate_mode(rtf_data, duplicates)`
- `_build_player_mapping(player, duplicates)`
- `_get_image_pool(ethnicity, nationality)`
- `pick_image_from_pools(pools, duplicates=False)`
- `pick_image(ethnicity, duplicates=False)`
- `get_xml_images(xml_data)`

#### Reporter
- `send_report(id)`

### UI-APP

#### NewGANManager
- `__init__()`
- `startup()`
- `_setup_application_data()`
- `_setup_menu()`
- `open_link(url)`
- `throw_error(msg)`
- `show_info(msg)`
- `on_exit()`
- `check_for_update()`

#### LogTab
- `__init__(app)`
- `_process_logs()`
- `_store_log(record)`
- `_update_ui(records)`
- `_on_log_level_changed(widget)`
- `_on_show_this_level_changed(widget)`
- `_open_log_file(widget)`
- `_clear_logs(widget)`

#### MainTab
- `__init__(app)`
- `set_btns(value=True)`
- `_create_profile(widget)`
- `_delete_profile(widget)`
- `_set_profile_status(e)`
- `_refresh_input_text(clear=False)`
- `_action_select_folder_dialog(widget)`
- `_action_open_file_dialog(widget)`
- `update_mode_info_by_selection(widget)`
- `_validate_rtf_file(rtf_path)`
- `_validate_image_directory(img_dir)`
- `_replace_faces(widget)`

## UML Class Diagrams

### Core Modules

```plantuml
@startuml
class ConfigManager {
  +load_config(path: str): dict
  +save_config(path: str, data: dict): None
  +get_latest_prf(path: str): str or None
}

class ProfileManager {
  +migrate_config(): None
  +delete_profile(name: str): bool
  +create_profile(name: str): None
  +load_profile(name: str): None
  +write_xml(data: list, backup: bool = True): list
  +swap_xml(deact_name: str, act_name: str, deact_img_dir: str, act_img_dir: str): None
  +get_ethnic(nation: str): str or None
}

class RtfParser {
  +parse_rtf(path: str): list
  +check_rtf_valid(path: str): bool
  +translate_rtf_data_to_english(rtf_data: list): list
}

class FaceMapper {
  +generate_mapping(rtf_data: list, mode: str, duplicates: bool = False): list
  +correct_ethnic(player: list, temp_eth1: str, temp_eth2: str): str
  +_process_preserve_mode(rtf_data: list, xml_data: dict, duplicates: bool): list
  +_process_overwrite_mode(rtf_data: list, xml_data: dict, duplicates: bool): list
  +_process_generate_mode(rtf_data: list, duplicates: bool): list
  +_build_player_mapping(player: list, duplicates: bool): list
  +_get_image_pool(ethnicity: str, nationality: str): list
  +pick_image_from_pools(pools: list, duplicates: bool = False): str
  +pick_image(ethnicity: str, duplicates: bool = False): str
  +get_xml_images(xml_data: dict): list
}

class Reporter {
  +send_report(id: str): str
}

ConfigManager --> ProfileManager : Inheritance
@enduml
```

### UI-APP Modules

```plantuml
@startuml
class NewGANManager {
  +__init__()
  +startup()
  +_setup_application_data()
  +_setup_menu()
  +open_link(url: str): None
  +throw_error(msg: str): None
  +show_info(msg: str): None
  +on_exit(): None
  +check_for_update(): None
}

class LogTab {
  +__init__(app)
  +_process_logs()
  +_store_log(record)
  +_update_ui(records)
  +_on_log_level_changed(widget)
  +_on_show_this_level_changed(widget)
  +_open_log_file(widget)
  +_clear_logs(widget)
}

class MainTab {
  +__init__(app)
  +set_btns(value: bool = True)
  +_create_profile(widget)
  +_delete_profile(widget)
  +_set_profile_status(e)
  +_refresh_input_text(clear: bool = False)
  +_action_select_folder_dialog(widget)
  +_action_open_file_dialog(widget)
  +update_mode_info_by_selection(widget)
  +_validate_rtf_file(rtf_path)
  +_validate_image_directory(img_dir)
  +_replace_faces(widget)
}

NewGANManager --> LogTab : Contains
NewGANManager --> MainTab : Contains
@enduml
```

## Improvements in Testing

- Write better tests

## Configuration File Usage

- Use one configuration file for nation-to-ethnicity mapping and another for the last active profile
