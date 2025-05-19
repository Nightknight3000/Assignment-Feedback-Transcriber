# Assignment Feedback

## Prerequisites
### Python
This tool is written in python (v3.11) and has thus to be run with python 3.\
It has the following requirements:

Packages:
* click
* pandas
* tabulate
* dash
* openpyxl
* dash-bootstrap-components
* selenium
* rich

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
Download all submissions from ILIAS (**Please make sure your language setting of ILIAS is English or Deutsch**). An `xlsx` file will also be created. Specify the files path in your config (see example: [example/config_example.txt](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/config_example.txt)), and run the script like this:
```

python3 assignment_feedback.py -l <lecture-marker> -c config.txt'
```
This will create a table for all xlsx specified in the configuration named `Assignment X` in a single database file named `<lecture-marker>.sqlite3`.
Then launch the web server through:
```
python3 assignment_feedback.py -l <lecture_marker> -w
```
**Important**: Always utilize the most recently-created empty database to run your webserver, if there have been changes to the number of xlsx-files. This ensures that all tables for newer xlsx-files are set up.\\
You may then merge older versions into it via the "Upload grading from other tutors"-button, to refill it with previous feedbacks.\\
Likewise you may merge the gradings from your colleagues.\\

Rule-of-thumb: Always use the database with the most tables in it, and merge the rest into them (since merging a database with more tables won't add these). 

### Manual Input - (Optional)
If you wish to use the tool without the web server, you require multiple CSV-files, each associated with an assignment. 
The CSV-files should each contain the reached points as well as the associated feedback of each task (see example: [example/grading_example.txt](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/grading_example.txt)).
#### The CLI - Command Line Interface
```
> python3 assignment_feedback.py [-l <str>] [-o <directorypath>] [-c <filepath>]
 
-l,    --lecture-marker,        string-marker to be added to output filenames, default="ssbi25"
-o,    --output-directory,      output directory for produced subdirectories and assignment feedbacks, default="example"
-c,    --config,                filepath to configuration file containing all specifications of the assignments, default='example/config_example.txt'
```
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
This tool returns all created feedbacks for the given assignments in Markdown format (see example: [example/ass1](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/ass1)). 

## Automatic upload
Finally, this tool allows to automatically upload the resulting feedbacks onto Ilias, by running:
```
> python3 assignment_feedback.py -u <path to directory containing the feedbacks>
```
**Note:** Running the script with this argument fully changes its mode of operation, i.e. it will be unable to perform Manual Input if called like this.

## Example
The webserver pipeline of this tool would look like this (requires specification of xlsx-files in config.txt):
```
# Setup database
> python3 assignment_feedback.py -l ssbi25 -c config.txt

# Run webserver utilizing the database
> python3 assignment_feedback.py -l ssbi25 -w
# TODO: Use GUI to input points and comments, then create feedback archive

# Upload feedback to Ilias
> python3 assignment_feedback.py -u feedback.zip
```

The manual pipeline for this tool would look like this (requires specification of csv-files containing points and comments in config.txt):
```
# For manual usage
> python3 assignment_feedback.py -c example/config_example.txt
```

## Authors
* **Alexander Röhl**
* **Haoran Sun**
