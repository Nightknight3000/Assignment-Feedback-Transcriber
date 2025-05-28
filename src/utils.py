import ast
import os
import re
import time

import pandas as pd
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException


_GERMAN_LANGUAGE_CONSTANTS = {'Vorname': 'First Name',
                              'Nachname': 'Last Name',
                              'Evaluation by File': 'Rückmeldung per Datei',
                              'back': 'zurück'}


def excel_to_sqlite(xlsx_file: str, db_connection, is_blank: bool = False) -> bool:
    try:
        df = pd.read_excel(xlsx_file, engine='openpyxl')
        if 'Grade' not in df.columns:
            df['Grade'] = ''
        df.insert(0, 'id', range(1, len(df) + 1))
        df.set_index('id', inplace=True)

        # Swap from german to english
        df = translate_df_columns_to_english(df)
        table_name = os.path.splitext(os.path.basename(xlsx_file))[0]
        if is_blank:
            # If new tables are added, drop new blank table if identically named one already exists
            try:
                df.to_sql(table_name, db_connection, if_exists='fail')
            except ValueError:
                pass
        else:
            df.to_sql(table_name, db_connection, if_exists='replace')
    except FileNotFoundError:
        print(f"Could not find {xlsx_file}")
        return False
    except Exception as e:
        print(f"Error importing Excel to SQLite: {str(e)}")
        return False
    finally:
        return True


def translate_df_columns_to_english(df: pd.DataFrame) -> pd.DataFrame:
    if 'Vorname' in df.columns:
        return df.rename(mapper=_GERMAN_LANGUAGE_CONSTANTS, axis=1)
    else:
        return df


def read_config(config: str) -> dict[str, list[str]]:
    assignments = {"nums": [], "files": [], "tasks": []}#, "ass_xl": []}
    with open(config, 'r') as f:
        lines = f.read().split('\n')
        for line in lines:
            if line.startswith('number='):
                num = int(line.replace('number=', ''))
                assignments['nums'].append(num)
            elif line.startswith('filepath='):
                assignments["files"].append(line.replace('filepath=', ''))
            elif line.startswith('max_points='):
                assignments["tasks"].append(ast.literal_eval(line.replace('max_points=', '')))
            # elif line.startswith('assignment_xlsx='):
            #     assignments["ass_xl"].append(line.replace('assignment_xlsx=', ''))
    if len(assignments["nums"]) != len(assignments["files"]) != len(assignments["tasks"]):
        raise IOError("Configuration must contain equal number of assignment numbers, filepaths, and max_points.")
    return assignments


def test_no_of_elements(lines: list[str], max_num: int) -> None:
    for i, line in enumerate(lines):
        if line:
            opened = False
            element_count = 0
            for c in line:
                if (not opened) and (c == '\"'):
                    opened = True
                elif opened and (c == '\"'):
                    opened = False
                elif (c == ',') and (not opened):
                    element_count += 1
            if element_count != max_num:
                print(line.split(','))
                raise Exception(f"Error! Found {element_count}, not the expected {max_num}, number of elements in line "
                                f"{i + 1} in your grading file.")


def upload_to_ilias(feedback_dir) -> None:
    print("Now the browser should open. Please log in to ILIAS and navigate to the course page.")
    driver = webdriver.Chrome()
    wait = WebDriverWait(driver, 20)

    driver.get("https://ovidius.uni-tuebingen.de/")
    print("Navigate to the Hands-in page and select the corresponding assignment.")

    # While waiting for the user
    per_team_feedbacks = {}
    for file in os.listdir(feedback_dir):
        team_number = file.split('_')[0]
        per_team_feedbacks[team_number] = os.path.join(os.path.abspath(feedback_dir), file)

    input("Press Enter when you are ready to upload feedbacks...")
    with Progress(TextColumn("[green]Uploading feedbacks..."),
                BarColumn(),
                MofNCompleteColumn()) as progress:
        task = progress.add_task("[green]Uploading feedbacks...", total=len(per_team_feedbacks))
        
        # Record the current URL for the RETURN functionality
        teams_view_url = urlparse(driver.current_url)
        teams_view_window = driver.current_window_handle
        table = wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table-responsive")))
        rows = table.find_elements(By.TAG_NAME, "tr")

        for team, feedback_file in per_team_feedbacks.items():
            for row in rows[1:]:
                # Find team name in small div with parentheses
                try:
                    small_div = row.find_element(By.CLASS_NAME, "small")
                    team_name_text = small_div.text
                    team_number = re.search(r'\((\d+)\)', team_name_text)

                    # In SSBI, only team submissions are accepted
                    if team_number:
                        team_number = team_number.group(1)
                        if team != team_number: continue

                        try:
                            button = row.find_element(By.XPATH, f".//button[normalize-space(text())='Evaluation by File']")
                        except NoSuchElementException:
                            button = row.find_element(By.XPATH, f".//button[normalize-space(text())='{_GERMAN_LANGUAGE_CONSTANTS['Evaluation by File']}']")

                        # open a new tab for uploading
                        upload_page_data_action = urlparse(button.get_attribute('data-action'))
                        upload_url = teams_view_url._replace(query=upload_page_data_action.query).geturl()
                        driver.switch_to.new_window('tab')
                        driver.get(upload_url)
                        for window_handle in driver.window_handles:
                            if window_handle != teams_view_window:
                                driver.switch_to.window(window_handle)
                                break
                        wait.until(EC.presence_of_element_located((By.ID, "new_file")))

                        # Upload feedback file
                        file_input = driver.find_element(By.ID, "new_file")
                        file_input.send_keys(feedback_file)
                        upload_button = driver.find_element(By.XPATH, "//input[@type='submit' and @name='cmd[uploadFile]']")
                        upload_button.click()
                        time.sleep(1)
                        wait.until(EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'alert-success')] | //table[contains(@class, 'table-striped')]//a")))

                        # Return
                        driver.close()
                        driver.switch_to.window(teams_view_window)
                        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "table-responsive")))

                        print(f"Successfully uploaded feedback for team {team}...", end='')
                        progress.advance(task)
                        print("progressing")
                        break

                except Exception as e:
                    print(f"Error processing {team}: {str(e)}")
