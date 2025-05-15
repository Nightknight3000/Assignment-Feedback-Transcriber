from dash import Dash, callback, html, Input, Output, State, dcc, ALL, ctx, MATCH, Patch, set_props
import pandas as pd
import dash
import os
import dash_bootstrap_components as dbc
import base64
import sqlite3
from assignment_feedback import read_config
import re
import json

def get_db_connection(db='ssbi25.sqlite3'):
    """Create a new database connection for the current thread"""
    connection = sqlite3.connect(db)
    connection.row_factory = sqlite3.Row
    return connection

db = get_db_connection()

# Get assignment names from the database
cursor = db.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
assignment_list = [table['name'] for table in tables]

app = Dash(__name__, external_scripts=[{
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

app.layout = dbc.Container([
    dcc.Download(id="downloader"),
    dbc.Modal(id="modal-view", size="lg", is_open=False, backdrop="static", centered=True),
    dbc.Toast("", id="toast-save", header="Info", is_open=False, duration=3000,
            style={"position": "fixed", "top": 66, "right": 10, "width": 350}),
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
        dbc.Col(
            dcc.Upload(
                html.Button('Upload grading from other tutors', className="btn btn-primary"),
                id='upload-db',style={'textAlign': 'center'}
            )
        ),
        dbc.Col(dbc.Button("Generate Feedbacks", id='generate', className="btn btn-primary", style={'width': '95%'}), className='col-2 mx-auto'),
    ], className='mt-3'),
    dbc.Row([
        dbc.Col([], id='submission-list', className='mx-auto'),
    ])
], id='main-content', fluid='xl')

@callback(Output('submission-list', 'children'),
        Input('assignment-select', 'value'),
        prevent_initial_call=True)
def get_submission_list(assignment):
    conn = get_db_connection()
    df = pd.read_sql_query(f"SELECT * FROM [{assignment}]", conn)
    # Check if 'Team' column exists
    if 'Team' in df.columns:
        # Group by Teams
        grouped_dfs = []
        for team, group in df.groupby('Team'):
            addViewButton = 0
            for index, row in group.iterrows():
                grouped_dfs.append({
                    "Graded": html.I(className="fa-solid fa-circle-info", id=f"graded_{team}") if addViewButton == 0 else "",
                    "First Name": row['First Name' if 'First Name' in group.columns else "Vorname"],
                    "Last Name": row['Last Name' if 'Last Name' in group.columns else "Nachname"],
                    "Team": team,
                    "": dbc.Button("View", id={'type': 'view-button', 'index': team}, className="btn btn-primary") if addViewButton == 0 else "",
                })
                addViewButton += 1
        df_new = pd.DataFrame(grouped_dfs)
        return dbc.Table.from_dataframe(df_new, striped=True, bordered=False, hover=True)
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

@callback(Output('modal-view', 'is_open'),
        Output('modal-view', 'children'),
        Input({'type': 'view-button', 'index': ALL}, 'n_clicks'),
        State('assignment-select', 'value'),
        prevent_initial_call=True)
def open_grading_modal(yes, assignment):
    for y in yes:
        if y != None:
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
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT [First Name], [Last Name], [Grade] FROM [{assignment}] WHERE Team = ?", (team,))
        students = cursor.fetchall()
        student_names = [f"{student['First Name']} {student['Last Name']}" for student in students]
    except sqlite3.Error as e:
        try:
            cursor.execute(f"SELECT [Vorname], [Nachname], [Grade] FROM [{assignment}] WHERE Team = ?", (team,))
            students = cursor.fetchall()
            student_names = [f"{student['Vorname']} {student['Nachname']}" for student in students]
        except sqlite3.Error as e:
            student_names = [f"Error loading students: {str(e)}"]
    
    # Get the scores and names from config files (or database maybe?)
    per_task_scores = read_config(os.path.join('ssbi25','config_ssbi25.txt'))['tasks'][assignment_num-1]
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

@callback(Output({'type': 'comment-placeholder', 'index': MATCH}, 'children'),
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
        dbc.Col(dbc.Input(type='text', placeholder='Comment', id={'type': 'comment-input', 'index': index}, value=comment), width=8, className='mt-1'),
    ], id={'type': 'comment-row', 'index': index})

@callback(Output({'type': 'comment-row', 'index': MATCH}, 'children'),
        Input({'type': 'remove-comment', 'index': MATCH}, 'n_clicks'),
        prevent_initial_call=True)
def remove_comment_row(n_clicks):
    if n_clicks is None:
        raise dash.exceptions.PreventUpdate
    return None

@callback(Input('save-button', 'n_clicks'),
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
    conn = get_db_connection()
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
    set_props('toast-save', {'children': "Feedback saved successfully!"})
    set_props(f'graded_{team_name}', {'className': 'fa-solid fa-check'})

@callback(Input('modal-view', 'is_open'),
          Input({'type': 'penalty-input', 'index': ALL}, 'value'),
        State({'type': 'comment-input', 'index': ALL}, 'id'),
        State('assignment-select', 'value'))
def update_score(ready_to_update, penalties, tasks, assignment):
    if not ready_to_update:
        raise dash.exceptions.PreventUpdate
    
    assignment_match = re.search(r'\d+$', assignment)
    assignment_id = int(assignment_match.group()) if assignment_match else None
    per_task_scores = read_config(os.path.join('ssbi25','config_ssbi25.txt'))['tasks'][assignment_id-1]

    penalties_gropued = {}
    for task, penalty in zip(tasks, penalties):
        if not task: continue
        task_id = task['index']
        task = task_id.split('_')[0]
        if task not in penalties_gropued:
            penalties_gropued[task] = []
        if type(penalty) == int:
            penalties_gropued[task].append(penalty)
    for task, penalty in penalties_gropued.items():
        total_penalty = sum(penalties_gropued[task])
        if total_penalty > 0: total_penalty = -total_penalty
        score = int(per_task_scores[task]) + total_penalty
        if score < 0:
            score = 0
        if score > int(per_task_scores[task]):
            score = int(per_task_scores[task])
        set_props({'type': 'per-task-total-score', 'index': task}, {'children': str(score)})


@callback(Input('upload-db', 'contents'),
          Input('upload-db', 'filename'),
          Input('upload-db', 'last_modified'),
          State('assignment-select', 'value'),
          prevent_initial_call=True)
def merge_grading_from_other_tutors(content, name, last_modified, assignment):
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)
    name = name + 'new'
    with open(name, 'wb') as f:
        f.write(decoded)
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
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
                    uploaded_grades = json.loads(uploaded_grade)
                    local_grades = json.loads(local_record['Grade']) if local_record['Grade'] else {}

                    for task, comments in uploaded_grades.items():
                        local_grades[task] = comments

                    cursor.execute(f"UPDATE [{assignment}] SET Grade = ? WHERE Team = ?", 
                                  (json.dumps(local_grades), team))
                except:
                    continue
        conn.commit()
        other_conn.close()

        set_props('toast-save', {'is_open': True})
        set_props('toast-save', {'children': "Grades from other tutors merged successfully!"})
    except sqlite3.Error as e:
        set_props('toast-save', {'is_open': True})
        set_props('toast-save', {'children': f"Error merging grades: {str(e)}"})
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

@callback(Output('downloader', 'data'),
        Input('generate', 'n_clicks'),
        prevent_initial_call=True)
def generate_feedback(generate):
    # TODO: Implement feedback generation logic
    # dcc.send_data_frame(df.to_csv, "mydf.csv")
    # dict(content="Hello world!", filename="hello.txt")

    # Or just generate a file on the disk but not download it?
    pass

if __name__ == '__main__':
    app.run(debug=True, port=8050)
