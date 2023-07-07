# Review Comment Classification Tool
This is the replication package for the paper "Towards Automated Classification of Code Review Feedback to Support Analytics", published in ESEM 2023.


## Datasets
The 'dataset' folder contains 'code_attributes.csv', 'labeled_dataset.csv', and 'codes.pkl' files and the 'Data New' folder. The 'code_attributes.csv' file contains the values for calculated code attributes. The 'labeled_dataset.xlsx' file contains the manually labeled dataset of code review comments from the OpenDev Nova project. The 'codes.pkl' file is required to run the main modeling code. The 'Data New' folder contains our dataset's source and destination code files.

## Scripts
'scripts' folder contains 'code_attribute_calculation' folder and 'comment_classification_model.ipynb' file. The 'code_attribute_calculation' folder contains the code for the code attribute calculation. The 'comment_classification_model.ipynb' file contains the code of our proposed model.

## Clone the project
Clone the project </br>
$ git clone https://github.com/WSU-SEAL/CR-classification-ESEM23.git

## Copyright Information
Copyright Software Engineering Analytics Lab (SEAL), Wayne State University, 2023
Authors: Asif Kamal Turzo <asifkamal@wayne.edu> and Amiangshu Bosu <abosu@wayne.edu> </br>

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
version 3 as published by the Free Software Foundation.
