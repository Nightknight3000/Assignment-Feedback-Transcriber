# Assignment Feedback

## Prerequisites
### Python
This tool is written in python (v3.11) and has thus to be run with python 3.\
It has the following requirements:

Packages:
* click
* pandas
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
```
Note: Both approaches need to refer to the pip-installer associated to the python installation, that will be used to run
the tool.


## Usage
### The CLI - Command Line Interface
```
> python3 assignment_feedback.py [-o <directorypath>] [-c <filepath>] 
  
-o,    --output-directory,      output directory for produced subdirectories and assignment feedbacks, default=""
-c,    --config,                filepath to configuration file containing all specifications of the assignments (see example: config.txt), default='config.txt'
```
### Input
This tool requires multiple CSV-files, each associated with assignment containing its feedback and the reached points 
of each task (see example: [example/grading_example.txt](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/grading_example.txt)).

The enumeration, the paths, and the maximum reachable points of each task need to be specified and given in a separate 
configuration file (see example: [example/config_example.txt](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/config_example.txt)).

### Output
This tool returns all created feedbacks for the given assignments in Markdown format (see example: [example/ass1](https://github.com/Nightknight3000/Assignment-Feedback-Transcriber/blob/main/example/ass1)). 

### Example
The tool can be run like this:
```
python3 assignment_feedback.py -c example/config_example.txt
python3 assignment_feedback.py -o /home/user/docs/all_feedbacks -c /home/user/docs/configuration.txt
```

## Authors
* **Alexander Röhl**
