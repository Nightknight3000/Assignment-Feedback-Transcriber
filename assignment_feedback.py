import click
from io import StringIO

from src.web_server import create_app
from src.utils import *


@click.command()
@click.option("-l", "--lecture-marker", default="ssbi25")
@click.option("-o", "--output-dir", default="example")
@click.option("-c", "--config", default="example/config_example.txt")
@click.option("-u", "--feedback-dir", help="The directory of feedbacks to upload", required=False)
@click.option("-w", "--web-server", is_flag=True, help="Start the web server for uploading feedback", default=False)
def main(lecture_marker, output_dir, config, feedback_dir, web_server):
    if feedback_dir:
        if not os.path.exists(feedback_dir):
            raise IOError(f"Feedback directory {feedback_dir} does not exist.")
        upload_to_ilias(feedback_dir)
    else:
      output_dir = output_dir + '/' if not output_dir.endswith('/') else output_dir
      assignments = read_config(config)
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

    if web_server:
        app = create_app(lecture_marker, output_dir, config)
        app.run(host='127.0.0.1', debug=False, port=8050)


if __name__ == "__main__":
    main()
