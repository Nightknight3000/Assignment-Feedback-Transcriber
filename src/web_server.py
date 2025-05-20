import os
import re
import json
import shutil
import base64
import secrets
import sqlite3
import zipfile
import pandas as pd

import dash
import dash_bootstrap_components as dbc
from dash import (ALL, MATCH, Dash, Input, Output, Patch, State, ctx, dcc,
                  html, set_props)
from flask import Flask, current_app, g

from src.utils import read_config, excel_to_sqlite


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def create_app(lecture_marker, output_dir, config):
    app = Flask(lecture_marker, instance_relative_config=True)
    app.config.from_mapping(
        DATABASE=os.path.join(output_dir, f'{lecture_marker}.sqlite3'),
        SECRET_KEY=secrets.token_hex(),
        LECTURE_CONFIG=config
    )
    print(os.path.abspath(app.config['DATABASE']))
    print(f"Database path: {app.config['DATABASE']}")

    with app.app_context():
        db = get_db()
    # Get assignment names from the database
    cursor = db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    assignment_list = [table['name'] for table in tables]

    dash_app = Dash(lecture_marker, server=app,
        external_scripts=[{
            'src': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/js/bootstrap.bundle.min.js',
            'integrity': 'sha384-HwwvtgBNo3bZJJLYd8oVXjrBZt8cqVSpeBNS5n7C8IVInixGAoxmnlMuBnhbgrkm',
            'crossorigin': 'anonymous'
        }],
        external_stylesheets=[{
            'href': 'https://cdn.jsdelivr.net/npm/bootstrap@5.3.1/dist/css/bootstrap.min.css',
            'integrity': 'sha384-4bw+/aepP/YC94hEpVNVgiZdgIC5+VKNBQNGCHeKRQN+PtmoHDEXuppvnDJzQIu9',
            'crossorigin': 'anonymous',
            'rel': 'stylesheet'
        },
        {
            'href': 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css',
            'rel': 'stylesheet'
        }],
        suppress_callback_exceptions=True)

    dash_app.layout = dbc.Container([
        dcc.ConfirmDialog(id='confirm-overwrite'),
        dcc.Download(id="downloader"),
        dbc.Modal(id="modal-view", size="lg", is_open=False, backdrop="static", centered=True),
        dbc.Toast("", id="toast-save", header="Info", is_open=False, duration=3000,
                  style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 9999}),
        dbc.Row([
            dbc.Col(html.H1("Assignment Feedback Transcriber"), className='text-center', width=12),
            dbc.Col(html.H4(f"Currently running on lecture {lecture_marker}"), width=12),
            dbc.Col(
                dbc.Row([
                    dbc.Col(
                        dcc.Upload(
                            html.Button('Add Assignment', className="btn btn-primary"),
                            id='upload-ass',style={'textAlign': 'center'}
                        ), width='auto'),
                    dbc.Col(
                        dcc.Upload(
                            html.Button('Merge Gradings', className="btn btn-primary"),
                            id='upload-db',style={'textAlign': 'center'}
                        ), width='auto'),
                ], className='justify-content-start'),
            width=6),
            dbc.Col(dbc.Button("Generate Feedbacks", id='generate', className="btn btn-primary", style={'width': '33%'}), width=6, className='d-flex justify-content-end'),
            dbc.Col(html.Hr(), width=12)
        ], className='mt-3 gy-3 justify-content-between'),
        dbc.Row([
            dbc.Col(html.Span("Select Assignment: ", className='h5'), width='auto'),
            dbc.Col([
                dbc.Select(
                    id="assignment-select",
                    options=[
                        {"label": assignment, "value": assignment} for assignment in assignment_list
                    ],
                ),
            ], className='col-2'),
        ], className='mt-3 mb-2 align-items-center'),
        dbc.Row([
            dbc.Col([], id='submission-list', className='mx-auto'),
        ])
    ], id='main-content', fluid='xl')

    @dash_app.callback(Output('submission-list', 'children'),
            Input('assignment-select', 'value'),
            prevent_initial_call=True)
    def get_submission_list(assignment):
        with app.app_context():
            conn = get_db()
        df = pd.read_sql_query(f"SELECT * FROM [{assignment}]", conn)

        assignment_match = re.search(r'\d+$', assignment)
        assignment_id = int(assignment_match.group()) if assignment_match else None
        per_task_scores = read_config(app.config['LECTURE_CONFIG'])['tasks'][assignment_id-1]

        # Check if 'Team' column exists
        if 'Team' in df.columns:
            # Group by Teams
            grouped_dfs = []
            for team, group in df.groupby('Team'):
                addViewButton = 0
                for index, row in group.iterrows():
                    try: feedbacks = json.loads(row['Grade'])
                    except: feedbacks = {}

                    # names and teams
                    row_dict = {
                        "Graded": html.I(className="fa-solid fa-circle-info" if not feedbacks else "fa-solid fa-check", id=f"graded_{team}") if addViewButton == 0 else "",
                        "First Name": row['First Name'],
                        "Last Name": row['Last Name'],
                        "Team": team,
                    }
                    # per task scores
                    for task, max_points in per_task_scores.items():
                        remaining_points = int(max_points)
                        if task not in feedbacks.keys():
                            row_dict[f"Task {task}"] = max_points
                        else:
                            for penalty, comment in feedbacks[task]:
                                if penalty is None:
                                    if comment is None: continue
                                    else: penalty = 0
                                if penalty >= 0: penalty = -penalty
                                remaining_points += penalty
                            if remaining_points < 0: remaining_points = 0
                            row_dict[f"Task {task}"] = remaining_points
                    row_dict[""] = dbc.Button("View", id={'type': 'view-button', 'index': team}, className="btn btn-primary") if addViewButton == 0 else ""
                    grouped_dfs.append(row_dict)
                    addViewButton += 1
            df_new = pd.DataFrame(grouped_dfs)
            return dbc.Table.from_dataframe(df_new, striped=True, bordered=False, hover=True)
        # logic for individual submissions haven't been implemented yet
        else:
            submission_cols = [col for col in df.columns if col.startswith('Submission')]
            if submission_cols:
                df = df.drop(columns=submission_cols)
            new_data = []
            for index, row in df.iterrows():
                row_dict = row.to_dict()
                row_dict[""] = dbc.Button("View", id={'type': 'view-button', 'index': f"{row['Last Name']},{row['First Name']}"}, className="btn btn-primary")
                new_data.append(row_dict)
            return dbc.Table.from_dataframe(pd.DataFrame(new_data), striped=True, bordered=False, hover=True)

    @dash_app.callback(Output('modal-view', 'is_open'),
            Output('modal-view', 'children'),
            Input({'type': 'view-button', 'index': ALL}, 'n_clicks'),
            State('assignment-select', 'value'),
            prevent_initial_call=True)
    def open_grading_modal(yes, assignment):
        for y in yes:
            if y is not None:
                break
        else:
            raise dash.exceptions.PreventUpdate
        triggered = ctx.triggered_id
        team = triggered['index']
        return True, get_grading_view(team, assignment)

    def get_grading_view(team, assignment):
        # Extract assignment number from the assignment name
        assignment_match = re.search(r'\d+$', assignment)
        assignment_num = int(assignment_match.group()) if assignment_match else None

        with app.app_context():
            conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute(f"SELECT [First Name], [Last Name], [Grade] FROM [{assignment}] WHERE Team = ?", (team,))
            students = cursor.fetchall()
            student_names = [f"{student['First Name']} {student['Last Name']}" for student in students]
        except sqlite3.Error as e:
            student_names = [f"Error loading students: {str(e)}"]

        # Get scores from config files
        per_task_scores = read_config(app.config['LECTURE_CONFIG'])['tasks'][assignment_num-1]
        try: grades = json.loads(students[0]['Grade'])
        except: grades = {}
        children = [
            dbc.ModalHeader([dbc.ModalTitle("Grading View for Team "), dbc.ModalTitle(team, id='team-name', className='ms-2')]),
            dbc.ModalBody(dbc.Container([
                dbc.Row([
                    dbc.Col(html.H5("Student Name: " + ", ".join(student_names)), className='col-auto'),
                    dbc.Col(dbc.Button("Save", id='save-button', className='btn btn-primary'), className='col-auto')
                ], className='d-flex justify-content-between align-items-center mb-5'),
            # task rows
            ] + [dbc.Row([
                    # task title and the button
                    dbc.Col(html.H3(f"Task {task}"), className='mx-auto col-3'),
                    dbc.Col(dbc.Button("Add Comment Line", id={'type': 'add-comment', 'index': task}, className='btn btn-secondary',
                                        # update n_clicks to match the comment saving state
                                        n_clicks=0 if len(grades) == 0 or not grades.get(task, False) else len(grades.get(task))
                                    ), className='mx-auto col-3'),
                    dbc.Col([html.Span(score, id={'type': 'per-task-total-score', 'index': task}), html.Span(f"/{score} points reached")], className='mx-auto col-6 align-items-center justify-content-end d-flex'),

                    # comments input boxes
                    html.Div(id={'type': 'comment-placeholder', 'index': task}) if len(grades) == 0 or not grades.get(task, False) else
                            # if there are saved comments, show them
                            html.Div([
                                get_comment_row(f"{task}_{i}", comment) for i, comment in enumerate(grades[task])
                            ], id={'type': 'comment-placeholder', 'index': task}),
                    # spacer
                    html.Hr(className='mt-3 mb-3'),
                ]) for task, score in per_task_scores.items()]
            ))
        ]
        return children

    @dash_app.callback(Output({'type': 'comment-placeholder', 'index': MATCH}, 'children'),
            Input({'type': 'add-comment', 'index': MATCH}, 'n_clicks'),
            prevent_initial_call=True)
    def add_comment_row(n_clicks):
        task = ctx.triggered_id['index']
        index = f"{task}_{n_clicks}"
        patched_children = Patch()
        patched_children.append(
            get_comment_row(index)
        )
        return patched_children

    def get_comment_row(index, comment=None):
        if not comment:
            penalty = None
        else:
            penalty = comment[0]
            comment = comment[1]
        return dbc.Row([
            dbc.Col(dbc.Button("❌", color='warning', id={'type': 'remove-comment', 'index': index}), width=1, className='mt-1'),
            dbc.Col(dbc.Input(type='number', placeholder='Penalty', id={'type': 'penalty-input', 'index': index}, value=penalty), width=3, className='mt-1'),
            dbc.Col(dbc.Textarea(placeholder='Comment', id={'type': 'comment-input', 'index': index}, value=comment), width=8, className='mt-1'),
        ], id={'type': 'comment-row', 'index': index}, className='align-items-center')

    @dash_app.callback(Output({'type': 'comment-row', 'index': MATCH}, 'children'),
            Input({'type': 'remove-comment', 'index': MATCH}, 'n_clicks'),
            prevent_initial_call=True)
    def remove_comment_row(n_clicks):
        if n_clicks is None:
            raise dash.exceptions.PreventUpdate
        return None

    @dash_app.callback(Input('save-button', 'n_clicks'),
            State({'type': 'penalty-input', 'index': ALL}, 'value'),
            State({'type': 'comment-input', 'index': ALL}, 'value'),
            State({'type': 'comment-input', 'index': ALL}, 'id'),
            State('team-name', 'children'),
            State('assignment-select', 'value'),
            prevent_initial_call=True)
    def save_gradings(save, penalties, comments, tasks, team_name, assignment):
        feedbacks = {}
        for task, penalty, comment in zip(tasks, penalties, comments):
            if not task: continue
            task_id = task['index']
            task = task_id.split('_')[0]
            if task not in feedbacks:
                feedbacks[task] = []
            feedbacks[task].append((penalty, comment))

        # Save the feedbacks to the database
        with app.app_context():
            conn = get_db()
        cursor = conn.cursor()

        # Before saving, check if the feedbacks already exist (for multiple tutor grading at the same time)
        # This way we can only add new comments but not overwrite the existing ones
        # existing_feedbacks = cursor.execute(f"SELECT Grade FROM [{assignment}] WHERE Team = ?", (team_name,)).fetchone()
        # if existing_feedbacks:
        #     existing_feedbacks = json.loads(existing_feedbacks['Grade'])
        #     existing_tasks = set(existing_feedbacks.keys())
        #     my_tasks = set(feedbacks.keys())
        #     # one tutor only responsible for their own tasks
        #     for task in existing_tasks - my_tasks:
        #         feedbacks[task] = existing_feedbacks[task]
        feedbacks_json = json.dumps(feedbacks)
        cursor.execute(f"UPDATE [{assignment}] SET Grade = ? WHERE Team = ?",
                        (feedbacks_json, team_name))
        conn.commit()
        conn.close()

        set_props('toast-save', {'is_open': True})
        set_props('toast-save',
                  {'children': html.Span([html.I(className="fa-solid fa-square-check me-1",
                                                 style={"color": "#63e6be"}), "Feedback saved successfully!"])})
        set_props(f'graded_{team_name}', {'className': 'fa-solid fa-check'})

    @dash_app.callback(Input('modal-view', 'is_open'),
                       Input({'type': 'penalty-input', 'index': ALL}, 'value'),
                       State({'type': 'comment-input', 'index': ALL}, 'id'),
                       State('assignment-select', 'value'))
    def update_score(ready_to_update, penalties, tasks, assignment):
        """
        Update the scores in the grading view after changing the penalties
        """
        if not ready_to_update:
            raise dash.exceptions.PreventUpdate

        assignment_match = re.search(r'\d+$', assignment)
        assignment_id = int(assignment_match.group()) if assignment_match else None
        per_task_scores = read_config(app.config['LECTURE_CONFIG'])['tasks'][assignment_id - 1]

        penalties_grouped = {}
        for task, penalty in zip(tasks, penalties):
            if not task: continue
            task_id = task['index']
            task = task_id.split('_')[0]
            if task not in penalties_grouped:
                penalties_grouped[task] = []
            if type(penalty) in [int, float]:
                penalties_grouped[task].append(penalty)
        for task, penalty in penalties_grouped.items():
            total_penalty = sum(penalties_grouped[task])
            if total_penalty > 0:
                total_penalty = -total_penalty
            score = float(per_task_scores[task]) + total_penalty
            if int(score) == float(score):
                score = int(score)
            if score < 0:
                score = 0
            if score > int(per_task_scores[task]):
                score = int(per_task_scores[task])
            set_props({'type': 'per-task-total-score', 'index': task}, {'children': str(score)})

    @dash_app.callback(Input('upload-ass', 'contents'),
                       Input('upload-ass', 'filename'),
                       Input('upload-ass', 'last_modified'),
                       prevent_initial_call=True)
    def add_assignment(content, xlsx_name, last_modified):
        """
        Upload the xlsx file to add an assignment
        """
        if not xlsx_name.endswith('.xlsx'):
            set_props('toast-save', {'is_open': True})
            set_props('toast-save', {'children': html.Span([html.I(
                className="fa-solid fa-square-xmark me-1", style={"color": "#ff3333"}),
                f"Unsupported file type! Please upload xlsx files."])})
        else:
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)
            with open(xlsx_name, 'wb') as f:
                f.write(decoded)
            with app.app_context():
                conn = get_db()
            table_name = os.path.splitext(os.path.basename(xlsx_name))[0]

            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            # If table doesn't exist, create it
            if not cursor.fetchone():
                if excel_to_sqlite(xlsx_name, conn):
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                    tables = cursor.fetchall()
                    assignment_list = [table['name'] for table in tables]
                    set_props('toast-save', {'is_open': True})
                    set_props('toast-save', {'children': html.Span([html.I(
                        className="fa-solid fa-square-check me-1", style={"color": "#63e6be"}),
                        f"{table_name} added successfully!"])})
                    set_props('assignment-select', {'options': [{"label": assignment, "value": assignment} for assignment in assignment_list]})
                else:
                    set_props('toast-save', {'is_open': True})
                    set_props('toast-save', {'children': html.Span([html.I(
                        className="fa-solid fa-square-xmark me-1", style={"color": "#ff3333"}),
                        f"Upload failed! Please check the log."])})

            # Otherwise, let the user determine whether to overwrite
            else:
                set_props('confirm-overwrite', {'displayed': True})
                set_props('confirm-overwrite', {'message': f"\"{table_name}\" already exists! \n"+
                                        "This is going to overwrite all your gradings. \n"+
                                        "Are you sure to proceed?"})

            if os.path.exists(xlsx_name):
                os.remove(xlsx_name)

    @dash_app.callback(Input('confirm-overwrite', 'submit_n_clicks'),
                       State('upload-ass', 'contents'),
                       State('upload-ass', 'filename'),
                       prevent_initial_call=True)
    def let_user_confirm_duplicate_action(proceed, content, xlsx_name):
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        with open(xlsx_name, 'wb') as f:
            f.write(decoded)

        with app.app_context():
            conn = get_db()
        table_name = os.path.splitext(os.path.basename(xlsx_name))[0]
        if excel_to_sqlite(xlsx_name, conn):
            set_props('toast-save', {'is_open': True})
            set_props('toast-save', {'children': html.Span([html.I(
                className="fa-solid fa-square-check me-1", style={"color": "#63e6be"}),
                f"{table_name} updated successfully!"])})
        else:
            set_props('toast-save', {'is_open': True})
            set_props('toast-save', {'children': html.Span([html.I(
                className="fa-solid fa-square-xmark me-1", style={"color": "#ff3333"}),
                f"Update failed! Please check the log."])})

        if os.path.exists(xlsx_name):
            os.remove(xlsx_name)


    @dash_app.callback(Input('upload-db', 'contents'),
                       Input('upload-db', 'filename'),
                       Input('upload-db', 'last_modified'),
                       State('assignment-select', 'value'),
                       prevent_initial_call=True)
    def merge_grading_from_other_tutors(content, name, last_modified, assignment):
        """
        Merge grading from other tutors into the current database
        """
        content_type, content_string = content.split(',')
        decoded = base64.b64decode(content_string)
        name = name + 'new'
        with open(name, 'wb') as f:
            f.write(decoded)
        with app.app_context():
            conn = get_db()
        cursor = conn.cursor()
        try:
            # Connect to the uploaded database
            other_conn = sqlite3.connect(name)
            other_conn.row_factory = sqlite3.Row
            other_cursor = other_conn.cursor()
            other_cursor.execute(f"SELECT Team, Grade FROM [{assignment}]")
            other_grades = other_cursor.fetchall()

            # Process each record from the uploaded database
            for row in other_grades:
                team = row['Team']
                uploaded_grade = row['Grade']

                if not uploaded_grade:
                    continue

                cursor.execute(f"SELECT Grade FROM [{assignment}] WHERE Team = ?", (team,))
                local_record = cursor.fetchone()

                if local_record:
                    try:
                        # In case the team have got full marks on all tasks
                        try: uploaded_grades = json.loads(uploaded_grade)
                        except: uploaded_grades = {}
                        try: local_grades = json.loads(local_record['Grade'])
                        except: local_grades = {}

                        # Only update the records that have penalties
                        for task, comments in uploaded_grades.items():
                            local_grades[task] = comments
                        cursor.execute(f"UPDATE [{assignment}] SET Grade = ? WHERE Team = ?",
                                    (json.dumps(local_grades), team))
                    except:
                        continue
            conn.commit()
            other_conn.close()

            set_props('toast-save', {'is_open': True})
            set_props('toast-save', {'children': html.Span([html.I(
                className="fa-solid fa-square-check me-1", style={"color": "#63e6be"}),
                "Grades from other tutors merged successfully!"])})
            set_props('submission-list', {'children': get_submission_list(assignment)})
        except sqlite3.Error as e:
            set_props('toast-save', {'is_open': True})
            set_props('toast-save', {'children': html.Span([html.I(
                className="fa-solid fa-square-xmark me-1", style={"color": "#ff3333"}),
                f"Error merging grades: {str(e)}"])})
        finally:
            # add connection close for second connection, in case sql operation failed without closing first
            try:
                other_conn.close()
            except sqlite3.Error:
                # connection already closed
                pass
            except NameError:
                # connection was never defined
                pass

            if os.path.exists(name):
                os.remove(name)

    @dash_app.callback(Output('downloader', 'data'),
                       Input('generate', 'n_clicks'),
                       State('assignment-select', 'value'),
                       prevent_initial_call=True)
    def generate_feedback(generate, assignment):
        if not assignment:
            set_props('toast-save', {'is_open': True})
            set_props('toast-save', {'children': "You need to select an assignment!"})
            return dash.no_update

        assignment_match = re.search(r'\d+$', assignment)
        assignment_id = int(assignment_match.group()) if assignment_match else None
        per_task_scores = read_config(app.config['LECTURE_CONFIG'])['tasks'][assignment_id - 1]

        os.makedirs('feedbacks', exist_ok=True)
        with app.app_context():
            conn = get_db()
        groups = pd.read_sql_query(f"SELECT [First Name], [Last Name], Team, Grade FROM [{assignment}]", conn)
        conn.close()

        for team, group in groups.groupby('Team'):
            members = group.reset_index(drop=True)
            student_names = [f"{student[1]['First Name']} {student[1]['Last Name']}"
                             for student in members.iterrows()]

            try:
                feedbacks = json.loads(members.at[0, 'Grade'])
            except:
                feedbacks = {}

            overall_score = 0
            markdown_str = f"# Feedback on {assignment} for Team {team}\n\n"
            markdown_str += f"Students: {', '.join(student_names)}\n\n"

            tasks_str = ''
            # Iterate through each task
            for task, max_points in per_task_scores.items():
                remaining_points = int(max_points)

                # Calculate the remaining points and update the comments
                penalty_str = "Penalties:\n\n"
                if task in feedbacks.keys():
                    for penalty, comment in feedbacks[task]:
                        if penalty is None:
                            if comment is None: continue    # Empty comment line
                            else: penalty = 0               # Comment with no penalty
                        if penalty >= 0:
                            penalty = -penalty
                        penalty_str += f"- **{penalty}** points: {comment}\n\n"
                        remaining_points += penalty
                    if remaining_points < 0:
                        remaining_points = 0

                tasks_str += f"## Task {task}\n\n"
                tasks_str += f"Points reached: **{remaining_points}/{max_points}**.\n\n"

                # Determine the displayed message based on the remaining points
                if remaining_points == int(max_points):
                    # In case the student has got full marks on this task,
                    # but the tutor still wants to leave a comment
                    if len(penalty_str) > 12:
                        tasks_str += penalty_str
                    tasks_str += f"Well done, you have got full marks on this task!\n\n"
                else:
                    tasks_str += penalty_str
                overall_score += remaining_points

            markdown_str += f"Overall Score: **{overall_score}/100**\n\n"
            markdown_str += tasks_str

            lastnames = [student[1]['Last Name'] for student in members.iterrows()]
            with open(os.path.join('feedbacks', f"{team}_{'_'.join(lastnames)}.md"), 'w') as f:
                f.write(markdown_str)
        # zip the files
        with zipfile.ZipFile(f"Feedbacks_{assignment}.zip", 'w') as zipf:
            for file in os.listdir('feedbacks'):
                zipf.write(os.path.join('feedbacks', file),
                           os.path.relpath(os.path.join('feedbacks', file), 'feedbacks'))
        # clean up
        with open(f"Feedbacks_{assignment}.zip", 'rb') as f:
            zip_byte = f.read()
        os.remove(f"Feedbacks_{assignment}.zip")
        shutil.rmtree('feedbacks', ignore_errors=True)

        return dcc.send_bytes(zip_byte, f"Feedbacks_{assignment}.zip")
    return app


if __name__ == '__main__':
    app = create_app('ssbi25', 'ssbi25', os.path.join('ssbi25', 'config_ssbi25.txt'))
    app.run(host='127.0.0.1', debug=True, port=8050)
