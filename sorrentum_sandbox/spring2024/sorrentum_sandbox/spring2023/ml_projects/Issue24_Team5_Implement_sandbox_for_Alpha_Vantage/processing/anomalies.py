import numpy as np
from pandas import DataFrame
from sklearn.ensemble import IsolationForest


def isolation_forest_labels(data: DataFrame):
    """
    Trains an Isolated Forest model on all the data
    and then returns labels of that same data using the
    classifier that was just computed

    Returns:
    np.array[Bool]
    """
    clf = IsolationForest(n_estimators=500, random_state=101)
    X = np.array(data.close).reshape(len(data), 1)
    clf.fit(X)
    return clf.predict(X) == 1


def quantiles(data: DataFrame):
    """
    Computes the quantiles and checks if each point
    is within +- 1.5 times the Interquartile range of the
    upper and lower quantiles, if its outside those ranges
    it is flagged as an outlier.

    Returns:
    np.array[Bool]
    """
    df = data.sort_values(by="close", ascending=True).reset_index()

    # Lower/upper quantile index
    Q1 = round(0.25 * len(df))
    Q3 = round(0.75 * len(df))

    # Actual value
    Q1 = df.iloc[Q1].close
    Q3 = df.iloc[Q3].close

    # Interquartile range and bounds
    iqr = Q3 - Q1
    upper = Q3 + (1.5 * iqr)
    lower = Q1 - (1.5 * iqr)

    X = np.array(df.close).reshape(len(df), 1)

    # Get labels for data
    labs = []
    for pt in X:
        if (pt > upper) or (pt < lower):
            labs.append(True)
            continue

        labs.append(False)

    return np.array(labs)
