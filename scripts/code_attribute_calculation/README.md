# AST-metrics-for-review-comments
This is the repo for the codebase that calculates the metrics.
Note that the data was included as part of the repo for transparency. Since it contains a lot of small files, cloning the repo may take time.


# Installation requirements
Gumtree jar is provided in the repository. It must be linked to run the project.

PythonParser is used as backend. Install from:

https://github.com/GumTreeDiff/pythonparser

Also, due to how Gumtree calls PythonParser, linux is required. After installing pythonparser, ensure that the PATH is set and you can call pythonparser from command line.

# Codebase
- Each metric calculator inherits from MetricCalculator.
- Each MetricCalculator works on a single src,dst pair at a time.
  - It is passed Diff, TreeClassifier, and PythonFileData objects for a src,dst pair
  - Details about Diff and TreeClassifier are available in Gumtree Wiki. 
  - PythonFileData is a custom class to contain some additional data(such as trees within line range).
- MetricRunner runs the metrics over the entire dataset(csv) and passes src,dst pairs to each MetricCalculator and  combines then to create the output CSV.
