import ast
import os
import re
import sqlite3

import pandas as pd
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TextColumn

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


_GERMAN_LANGUAGE_CONSTANTS = {'Vorname': 'First Name',
                              'Nachname': "Last Name"}


def excel_to_sqlite(xlsx_file: str, sqlite_file: str) -> None:
    try:
        df = pd.read_excel(xlsx_file, engine='openpyxl')
        df['Grade'] = ''
        df.insert(0, 'id', range(1, len(df) + 1))
        df.set_index('id', inplace=True)

        # Swap from german to english
        df = translate_df_columns_to_english(df)

        table_name = os.path.splitext(os.path.basename(xlsx_file))[0]
        conn = sqlite3.connect(sqlite_file)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Successfully imported {xlsx_file} into {sqlite_file} as table '{table_name}'")
        conn.close()
    except FileNotFoundError:
        print(f"Could not find {xlsx_file}")
    except Exception as e:
        print(f"Error importing Excel to SQLite: {str(e)}")


def translate_df_columns_to_english(df: pd.DataFrame) -> pd.DataFrame:
    if 'Vorname' in df.columns:
        return df.rename(mapper=_GERMAN_LANGUAGE_CONSTANTS, axis=1)
    else:
        return df



def read_config(config: str, lecture_marker: str = '') -> dict[str, list[str]]:
    assignments = {"nums": [], "files": [], "tasks": [], "ass_xl": []}
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
            elif line.startswith('assignment_xlsx='):
                assignments["ass_xl"].append(line.replace('assignment_xlsx=', ''))
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
    driver = webdriver.Edge()
    driver.get("https://ovidius.uni-tuebingen.de/")
    print("Navigate to the Hands-in page and select the corresponsing assignment.")

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
        for team, feedback_file in per_team_feedbacks.items():
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "table-responsive"))
            )
            rows = table.find_elements(By.TAG_NAME, "tr")

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

                        driver.execute_script("arguments[0].scrollIntoView(true);", row)
                        driver.implicitly_wait(1)

                        # Actions dropdown
                        actions_cell = row.find_element(By.XPATH, ".//td[contains(.//div/@class, 'dropdown')]")
                        dropdown_button = actions_cell.find_element(By.XPATH, ".//button[contains(@class, 'dropdown-toggle')]")
                        try: dropdown_button.click()
                        except Exception: driver.execute_script("arguments[0].click();", dropdown_button)
                        driver.implicitly_wait(1)

                        # Evaluation by File
                        evaluation_button = row.find_element(By.XPATH, ".//button[contains(text(), 'Evaluation by File')]")
                        try: evaluation_button.click()
                        except Exception: driver.execute_script("arguments[0].click();", evaluation_button)
                        driver.implicitly_wait(1)

                        # Upload feedback file
                        file_input = driver.find_element(By.ID, "new_file")
                        file_input.send_keys(feedback_file)
                        upload_button = driver.find_element(By.XPATH, "//input[@type='submit' and @name='cmd[uploadFile]']")
                        upload_button.click()
                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'alert-success')] | //table[contains(@class, 'table-striped')]//a"))
                        )

                        # Return
                        print(f"Successfully uploaded feedback for team {team_number}")
                        driver.back()
                        WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "table-responsive"))
                        )
                        progress.advance(task)
                        break

                except Exception as e:
                    print(f"Error processing row: {str(e)}")
