# Efficient-Code-Generation-with-E-Code

## DataSet
  Since efficient code generation is a new branch that is opened for code generation, we curate a new dataset of efficient code generation programming problems called ECG for fine-tuning and evaluation. Accordingly, our model is fine-tuned on the ECG dataset. 
  
  The ECG draws on the APPS dataset (Hendrycks et al., 2021) and the CodeContests dataset (Li et al., 2022). We describe the dataset creation process and creative ideas in detail in Readme for DataSet folder.

  Although we developed the ECG dataset to perform efficient code generation, the ECG dataset is an exhaustive dataset that can be applied to different tasks. Therefore, we derived three datasets from this feature of the ECG dataset that can be applied to different specific code processing tasks to fill the gap of other code processing-oriented datasets.
  
  Among the ECG datasets our model uses for efficient code generation, we derive three datasets from them: ECG-CG, ECG-mini, and ECG-clone. We present each dataset in Readme for DataSet folder, respectively.
  
See the Readme file in [DataSet/README](https://github.com/CodeGeneration2/Efficient-Code-Generation-with-E-Code/main/DataSet/README.md)


## How to Use
The training prediction code is in the [Training prediction code](https://github.com/CodeGeneration2/Efficient-Code-Generation-with-E-Code/tree/main/Training%20prediction%20code) folder, and the details of how to use it are in the [Training prediction code/README](https://github.com/CodeGeneration2/Efficient-Code-Generation-with-E-Code/blob/main/Training%20prediction%20code/README.md)


## Diagrammatic figure
The diagrammatic figure is in the [Diagrammatic figure](https://github.com/CodeGeneration2/Efficient-Code-Generation-with-E-Code/tree/main/Diagrammatic%20figure) folder.


## Generated code has been predicted
The author has trained the model to predict the generated code is in the [Generated code has been predicted](https://github.com/CodeGeneration2/Efficient-Code-Generation-with-E-Code/tree/main/Generated%20code%20has%20been%20predicted) folder.
