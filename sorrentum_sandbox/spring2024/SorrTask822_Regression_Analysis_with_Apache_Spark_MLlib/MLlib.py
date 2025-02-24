from pyspark.sql import SparkSession
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.classification import RandomForestClassifier
from pyspark.ml.evaluation import MulticlassClassificationEvaluator
from pyspark.ml.feature import VectorAssembler
from ucimlrepo import fetch_ucirepo
import numpy as np
import pandas as pd
import findspark

# Initialize spark dependencies with findspark
findspark.init()

# Initialize a SparkSession
spark = SparkSession.builder.getOrCreate()

# Pulling data from UCI database and converting to Spark Dataframe format
wine = fetch_ucirepo(id=109)
X = wine.data.features
y = wine.data.targets
data = spark.createDataFrame(pd.concat([X, y], axis=1))

# Using columns 1-12 as variables and the last column as data labels for prediction,
# import the VectorAssembler class and create an array of features
assembler = VectorAssembler(inputCols=data.columns[:-1], outputCol='features')
data = assembler.transform(data)

# Split the train set and test set using the RandomSplit function
train, test = data.randomSplit([0.7, 0.3])

# Importing Logistic Regression model from the Spark library
LR = LogisticRegression(featuresCol='features', labelCol='class')

# Train the model
model_lr = LR.fit(train)

# Get the evaluation of model
eva = model_lr.evaluate(test)

# Get the result of data
result = eva.predictions

# Output the accuracy
print("The accuracy for logistic regression is %f.\n" % eva.accuracy)

# Importing Random Forest model
RF = RandomForestClassifier(featuresCol='features', labelCol='class', numTrees=50)

# Train the model
model_rf = RF.fit(train)

# Get the prediction of test set label
prediction = model_rf.transform(test)
evaluator = MulticlassClassificationEvaluator(
    labelCol='class', metricName='accuracy'
)
accuracy = evaluator.evaluate(prediction)
print("The accuracy for Random Forest is %f.\n" % accuracy)
