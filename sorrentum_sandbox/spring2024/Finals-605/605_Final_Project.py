#This code is taken from colab is you intend to use colab then remove the three lines below from comments
#!pip intsall pyspark
#!pip install graphframes

from pyspark.sql import SparkSession
from graphframes import GraphFrame

spark = SparkSession.builder.master("local[*]").config("spark.jars.packages", "graphframes:graphframes:0.8.2-spark3.2-s_2.12").getOrCreate()

import random
from graphframes import GraphFrame
from pyspark.sql import SparkSession

# Generate random city names
city_names = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville", "San Francisco", "Indianapolis", "Seattle"]

# Generate random coordinates for cities
cities = []
for i, name in enumerate(city_names):
    cities.append((str(i + 1), name, random.uniform(0, 100), random.uniform(0, 100)))

# Define DataFrame for vertices with city names, coordinates, and cost
spark = SparkSession.builder.master("local[*]").appName("Graph").getOrCreate()
vertices = spark.createDataFrame(cities, ["id", "name", "x", "y"])

# Define a cost function for vertices (random in this example)
def cost_function():
    return random.randint(1, 10)

# Add cost column to vertices DataFrame
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType

cost_udf = udf(cost_function, IntegerType())
vertices = vertices.withColumn("cost", cost_udf())

# Define DataFrame for edges with distances between cities
edges = []
for i in range(len(cities)):
    for j in range(i + 1, len(cities)):
        distance = ((cities[i][2] - cities[j][2]) ** 2 + (cities[i][3] - cities[j][3]) ** 2) ** 0.5
        # Introduce randomness in connections by randomly removing some edges
        if random.random() < 0.8:  # Adjust the probability to control the randomness of connections
            edges.append((str(i + 1), str(j + 1), distance))

edges_df = spark.createDataFrame(edges, ["src", "dst", "distance"])

# Create GraphFrame
g = GraphFrame(vertices, edges_df)


g.vertices.show()
g.edges.show()

import networkx as nx
import matplotlib.pyplot as plt

# Convert vertices and edges DataFrames to pandas DataFrames
vertices_pd = g.vertices.toPandas()
edges_pd = g.edges.toPandas()

# Create a NetworkX graph
G = nx.Graph()

# Add nodes to the graph
for _, row in vertices_pd.iterrows():
    G.add_node(row['id'], name=row['name'], x=row['x'], y=row['y'], cost=row['cost'])

# Add edges to the graph
for _, row in edges_pd.iterrows():
    src_id = row['src']
    dst_id = row['dst']
    src_name = vertices_pd[vertices_pd['id'] == src_id]['name'].iloc[0]
    dst_name = vertices_pd[vertices_pd['id'] == dst_id]['name'].iloc[0]
    G.add_edge(src_id, dst_id, distance=row['distance'], src_name=src_name, dst_name=dst_name)

# Draw the graph
plt.figure(figsize=(12, 8))

# Define positions of nodes
pos = nx.spring_layout(G, seed=42)

# Draw nodes
nx.draw_networkx_nodes(G, pos, node_size=300, node_color='lightblue')

# Draw edges
nx.draw_networkx_edges(G, pos, width=1.0, alpha=0.5)

# Draw node labels
node_labels = nx.get_node_attributes(G, 'name')
nx.draw_networkx_labels(G, pos, labels=node_labels, font_size=10, font_weight='bold')

# Draw edge labels
edge_labels = nx.get_edge_attributes(G, 'distance')
nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)

plt.title('Graph Visualization')
plt.axis('off')
plt.show()

# Run PageRank algorithm
results = g.pageRank(resetProbability=0.15, tol=0.01)

# Display the PageRank score for each vertex
results.vertices.show()


# Find shortest paths from a source vertex
shortest_paths = g.shortestPaths(landmarks=["1"])
shortest_paths.show()


node_degrees = nx.degree(G)
node_degrees_with_city_names = [(city_names[int(node) - 1], degree) for node, degree in node_degrees]
print("Node Degrees with City Names:", node_degrees_with_city_names)

# Compute centrality measures like degree centrality, betweenness centrality, and closeness centrality
degree_centrality = nx.degree_centrality(G)
betweenness_centrality = nx.betweenness_centrality(G)
closeness_centrality = nx.closeness_centrality(G)
# Print centrality measures
print("Degree Centrality:")
for city, centrality in degree_centrality.items():
    city_name = vertices_pd[vertices_pd['id'] == city]['name'].iloc[0]
    print(f"City {city_name}: {centrality}")

print("\nBetweenness Centrality:")
for city, centrality in betweenness_centrality.items():
    city_name = vertices_pd[vertices_pd['id'] == city]['name'].iloc[0]
    print(f"City {city_name}: {centrality}")

print("\nCloseness Centrality:")
for city, centrality in closeness_centrality.items():
    city_name = vertices_pd[vertices_pd['id'] == city]['name'].iloc[0]
    print(f"City {city_name}: {centrality}")


# Print schema of the vertices DataFrame
print("Vertices Schema:")
vertices.printSchema()

# Print schema of the edges DataFrame
print("\nEdges Schema:")
edges_df.printSchema()

from collections import deque
import pandas as pd
from pyspark.sql import functions as F  # Importing PySpark SQL functions module

def bfs(graph, start_vertex):
    # Extract the adjacency list from the GraphFrame
    adjacency_list = graph.edges.groupBy("src").agg(F.collect_list("dst").alias("neighbors")).toPandas()
    adjacency_list = dict(zip(adjacency_list["src"], adjacency_list["neighbors"]))

    visited = set()  # Set to keep track of visited vertices
    queue = deque([(start_vertex, 0)])  # Queue for BFS traversal, starting vertex with its depth
    traversal_steps = []  # List to store traversal steps

    while queue:
        vertex, depth = queue.popleft()  # Dequeue a vertex and its depth
        visited.add(vertex)  # Mark the vertex as visited
        traversal_steps.append((vertex, depth))  # Add vertex and its depth to traversal steps

        for neighbor in adjacency_list.get(vertex, []):
            if neighbor not in visited:
                queue.append((neighbor, depth + 1))  # Enqueue neighbor with increased depth

    return traversal_steps

# Perform BFS traversal starting from vertex '1'
bfs_steps = bfs(g, '1')

# Convert traversal steps to DataFrame
bfs_df = pd.DataFrame(bfs_steps, columns=['Vertex', 'Depth'])

# Display the BFS traversal steps
print("BFS Traversal:")
print(bfs_df)

from collections import deque
import pandas as pd
from pyspark.sql import functions as F  # Importing PySpark SQL functions module

def dfs(graph, start_vertex):
    # Extract the adjacency list from the GraphFrame
    adjacency_list = graph.edges.groupBy("src").agg(F.collect_list("dst").alias("neighbors")).toPandas()
    adjacency_list = dict(zip(adjacency_list["src"], adjacency_list["neighbors"]))

    visited = set()  # Set to keep track of visited vertices
    stack = [(start_vertex, 0)]  # Stack for DFS traversal, starting vertex with its depth
    traversal_steps = []  # List to store traversal steps

    while stack:
        vertex, depth = stack.pop()  # Pop a vertex and its depth from the stack
        visited.add(vertex)  # Mark the vertex as visited
        traversal_steps.append((vertex, depth))  # Add vertex and its depth to traversal steps

        for neighbor in reversed(adjacency_list.get(vertex, [])):
            if neighbor not in visited:
                stack.append((neighbor, depth + 1))  # Push neighbor with increased depth to the stack

    return traversal_steps

# Perform DFS traversal starting from vertex '1'
dfs_steps = dfs(g, '1')

# Convert traversal steps to DataFrame
dfs_df = pd.DataFrame(dfs_steps, columns=['Vertex', 'Depth'])

# Display the DFS traversal steps
print("DFS Traversal:")
print(dfs_df)

clustering = g.labelPropagation(maxIter=5)
clustering.select("id", "label").show()

# Create a NetworkX graph using your variables
nx_graph = nx.Graph()

# Add nodes to the graph
for _, row in vertices_pd.iterrows():
    nx_graph.add_node(row['id'], name=row['name'], x=row['x'], y=row['y'], cost=row['cost'])

# Add edges to the graph
for _, row in edges_pd.iterrows():
    src_id = row['src']
    dst_id = row['dst']
    src_name = vertices_pd[vertices_pd['id'] == src_id]['name'].iloc[0]
    dst_name = vertices_pd[vertices_pd['id'] == dst_id]['name'].iloc[0]
    nx_graph.add_edge(src_id, dst_id, distance=row['distance'], src_name=src_name, dst_name=dst_name)

# Calculate Network Density
density = nx.density(nx_graph)
print("Network Density:", density)

# Calculate Average Shortest Path Length
average_shortest_path_length = nx.average_shortest_path_length(nx_graph)
print("Average Shortest Path Length:", average_shortest_path_length)

# Calculate Clustering Coefficient
clustering_coefficient = nx.average_clustering(nx_graph)
print("Clustering Coefficient:", clustering_coefficient)
