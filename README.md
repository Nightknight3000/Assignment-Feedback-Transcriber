# Assignment Feedback

*CLAUDIO*, the tool for "**C**ross-**l**inking **a**nalysis **u**sing **di**stances and **o**verlaps", allows
for a methodical stepwise evaluation of cross-linking interaction types via in-depth analysis of structure and sequence 
information. It returns structural restraints, which can be applied in structure predictions, and the input dataset
extended by its analysis' results. 

## Prerequisites
### Python
This tool is written in python (v3.11) and has thus to be run with python 3.\
It has the following requirements:

Packages:
* click
* pandas

The packages may be installed all at once with the file requirements.txt:
```
pip install -r requirements.txt
```
or individually:
```
pip install click
pip install pandas
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
of each task (see example: data/grading_example.txt).

The enumeration, the paths, and the maximum reachable points of each task need to be specified and given in a separate 
configuration file (see example: config.txt).

### Output
This tool returns all created feedbacks for the given assignments in Markdown format. 

### Example
**CLAUDIO** (in full) can be run like this:
```
python3 assignment_feedback.py -c config.txt
python3 assignment_feedback.py -o /home/user/docs/all_feedbacks -o /home/user/docs/configuration.txt
```

## Authors
* **Alexander Röhl**
