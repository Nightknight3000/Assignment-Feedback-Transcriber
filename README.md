# Assignment Feedback

## Prerequisites
### Python
This tool is written in python (v3.11) and has thus to be run with python 3.\
It has the following requirements:

Packages:
* click
* dash
* dash-bootstrap-components
* flask
* openpyxl
* rich
* pandas
* selenium
* tabulate

The packages may be installed all at once with the file [requirements.txt](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/requirements.txt):
```
pip install -r requirements.txt
```
or individually:
```
pip install click
pip install pandas
pip install tabulate
pip install dash
pip install openpyxl
pip install dash-bootstrap-components
pip install selenium
pip install rich
```
Note: Both approaches need to refer to the pip-installer associated to the python installation, that will be used to run
the tool.

## Input
### Input through Web service - (Recommended)
Download all submissions from ILIAS (**Please make sure your language setting of ILIAS is English or Deutsch**). An `xlsx` file will also be created. Specify the tasks and their points for each assignment in your config (see example: [example/config_example.txt](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/config_example.txt)), and run the script like this to start the web server:

```
python3 assignment_feedback.py -m websever -l <lecture-marker> -o <directorypath> -c <filepath>
```

This will create a database file named `-l <lecture-marker>.sqlite3` in `-o <directorypath>`.
Then click `Add Assignment` button on the web server and upload `Assignment ?.xlsx`, which you obtained from ILIAS. 

**NOTE:** If the assignment already exists in the database, the system will prompt you whether to overwrite it.

You may merge the gradings from your colleagues. Click `Merge Gradings` button on the webpage, then upload the `sqlite3` database file. then the incoming gradings for the current selected assignment will be merged. 

**Rule-of-thumb:** Always use the database with the most tables in it, and merge the rest into them (since merging a database with more tables won't add these). 

After all the gradings for one assignment have been finished, click the `Generate Feedbacks` button to download the feedback files. You will get a `zip` file for unpacking. Now you can stop the web server and upload them to ILIAS. See [Automatic upload](#automatic-upload).

### Manual Input through legacy mode - (Optional)
If you wish to use the tool without the web server, you require multiple CSV-files, each associated with an assignment. 
The CSV-files should each contain the reached points as well as the associated feedback of each task (see example: [example/grading_example.txt](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/grading_example.txt)).
```
> python3 assignment_feedback.py -m legacy -l <lecture-marker> -o <directorypath> -c <filepath>
```
#### Input CSV Formatting
The provided information on points and feedback should be split by a comma and each surrounded by quotation-marks (to allow for the use of regular comma without breaking the format):
* List of all group members: \
  ``"<member_1>,<member_2>,<member_X>"``
* Feedbacks for each task (3 options)
  * simply returning points reached: \
    ``"<total_task_points_reached>"``
  * returning points reached with single-line comment: \
    ``"<total_task_points_reached>:<points_substracted> <comment>"``
  * returning points reached with multiple lines of comments (by splitting with a '|'-symbol): \
    ``"<total_task_points_reached>:<first line pts_substr> <first line comment>|<second line pts_substr> <second line comment>"``

The enumeration, the paths, and the maximum reachable points of each task need to be specified and given in a separate 
configuration file (see example: [example/config_example.txt](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/config_example.txt)).

## Output
This tool returns all created feedbacks for the given assignments in Markdown format (see example (for legacy mode): [example/ass1](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/ass1)). 

## Automatic upload
Finally, this tool allows to automatically upload the resulting feedbacks onto Ilias, by running:
```
> python3 assignment_feedback.py -m feedback -u <feedback directorypath>
```
For this to work, the feedback files in the specified directory should contain the team's id as the prefix of each file's name (webserver outputs should have those automatically).

## Example
The webserver pipeline of this tool could look like this:
```
# Start webserver and setup database in outputdirectory (here='outs')
> python3 assignment_feedback.py -l lecture -o outs -c lecture_config.txt
# TODO: Use GUI to load xlsx-files downloaded form Ilias, input points and comments, then create and unpack feedback archive.

# Upload feedback to Ilias by specifying the unpacked directory
> python3 assignment_feedback.py -m feedback -u 'Feedbacks_Assignment X'
```

The legacy pipeline for this tool could look like this (requires specification of csv-files (see [format specifications](#input-csv-formatting)) in config.txt):
```
# For legacy usage
> python3 assignment_feedback.py -m legacy -l lecture -o outs -c lecture_config.txt
# TODO: Manually add team id to created output feedback file's names as prefix.

# Upload feedback to Ilias by specifying the renamed feedbacks' directory
> python3 assignment_feedback.py -m feedback -u 'outs/assX'
```

## Authors
* **Alexander Röhl**
* **Haoran Sun**
