import ast
import os
import click
import pandas as pd
import sqlite3
from io import StringIO


@click.command()
@click.option("-l", "--lecture-marker", default="ssbi25")
@click.option("-o", "--output-dir", default="example")
@click.option("-c", "--config", default="example/config_example.txt")
def main(lecture_marker, output_dir, config):

    output_dir = output_dir + '/' if not output_dir.endswith('/') else output_dir
    assignments = read_config(config, lecture_marker)
    database_name = f"{lecture_marker}.sqlite3"

    for i in range(len(assignments["nums"])):
        failed = False
        assignment_no = assignments["nums"][i]
        filepath = assignments["files"][i]
        tasks_and_max_points = assignments["tasks"][i]

        # Check whether Ilias Assignment excel was given
        try:
            assignment_xlsx = assignments["ass_xl"][i]
        except IndexError:
            assignment_xlsx = None
            print(f"No path specified for Ilias assignment excel for assignment no.{assignment_no}.\n"
                  f"Skipping database table creation.")

        # If Ilias Assignment excel was given, attempt to create database
        if assignment_xlsx:
            try:
                excel_to_sqlite(assignment_xlsx, output_dir + database_name)
            except ValueError:
                print("Error: Database option format must be 'xlsx_file:sqlite_file'")

        empty_table_str = "task,points_reached,points_max,comment\n"
        for task, max_points in tasks_and_max_points.items():
            empty_table_str += f"{task},,{max_points},\n"
        empty_table = pd.read_csv(StringIO(empty_table_str),
                                  sep=',',
                                  index_col=False,
                                  dtype={'task': int, 'points_reached': float, 'points_max': float, 'comment': str})

        if os.path.exists(filepath):
            # sanity test
            test_no_of_elements(open(filepath, 'r').read().split('\n'), len(tasks_and_max_points))

            try:
                df = pd.read_csv(filepath, sep=',', index_col=0)
            except pd.errors.ParserError as e:
                raise IOError(f"Unable to parse csv {filepath} with pandas (Message: {e})")
            for names, point_list in {name: {task: df.loc[name, task] for task in df.columns} for name in df.index}.items():
                for name in names.split(','):
                    out_str = ''
                    for task, point_comment in point_list.items():
                        if ':' in str(point_comment):
                            points, comment = point_comment.split(':', 1)
                        else:
                            points = point_comment
                            comment = ''
                        comment = comment.replace('|', '\n')
                        empty_table.loc[int(task) - 1, "points_reached"] = float(points)
                        empty_table.loc[int(task) - 1, "comment"] = str(comment)
                    out_str += empty_table.to_markdown(index=None)
                    try:
                        total_points_reached = empty_table["points_reached"].astype(float).sum()
                        total_max_points = empty_table["points_max"].astype(float).sum()
                        out_str += f'\nTotal points reached: {total_points_reached} of {total_max_points}'
                    except ValueError:
                        print(f"Found non-floatable value in feedback for {name}.")
                        continue

                    if (total_points_reached <= total_max_points) and ("TODO" not in out_str):
                        if not os.path.exists(f"{output_dir}ass{assignment_no}"):
                            os.mkdir(f"{output_dir}ass{assignment_no}")
                        with open(f"{output_dir}ass{assignment_no}/{lecture_marker}_ass{assignment_no}_feedback_{name}.md", 'w') as f:
                            f.write(out_str)
                    elif total_points_reached > total_max_points:
                        print(f"Error. Total points calculated exceed total points intended:\n{out_str}\n")
                    elif "TODO" in out_str:
                        print(f"Error. Found TODO in output:\n{out_str}\n")
                    else:
                        print(f"Unknown Error in output:\n{out_str}\n")
        else:
            print(f"Could not find {filepath}.")
            failed = True
        if not failed:
            print(f"Finished writing outputs for {filepath}.")


def excel_to_sqlite(xlsx_file: str, sqlite_file: str) -> None:
    try:
        df = pd.read_excel(xlsx_file, engine='openpyxl')
        df['Grade'] = ''
        table_name = os.path.splitext(os.path.basename(xlsx_file))[0]
        conn = sqlite3.connect(sqlite_file)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Successfully imported {xlsx_file} into {sqlite_file} as table '{table_name}'")
        conn.close()
    except FileNotFoundError:
        print(f"Could not find {xlsx_file}")
    except Exception as e:
        print(f"Error importing Excel to SQLite: {str(e)}")


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



if __name__ == "__main__":
    main()
