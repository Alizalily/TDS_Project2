# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "requests",
#   "pandas",
#   "matplotlib",
#   "seaborn",
#   "python-dotenv",
# ]
# ///

from dotenv import load_dotenv
import argparse
import os
import pandas as pd
import json
import requests
import matplotlib.pyplot as plt
import seaborn as sns

# Ensure the script's directory is the working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

# Create output directory
output_dir = "output"
os.makedirs(output_dir, exist_ok=True)

# Load environment variables from the .env file
load_dotenv()

# Fetch the API key from the environment
api_key = os.getenv("OPENAI_API_KEY")

# Check if API key is successfully loaded
if not api_key:
    print("Error: API key not found. Make sure it's set in the .env file.")
    exit()

# Argument parser for command-line input
parser = argparse.ArgumentParser(description='Analyze a dataset and generate insights.')
parser.add_argument('file_path', type=str, help='The file path of the dataset (e.g., dataset.csv)')

args = parser.parse_args()
file_path = args.file_path

# User input for file path
#file_path = input("Enter the file path of your dataset (e.g., 'house-rent.csv'): ")

# Dictionary mapping file extensions to their respective read functions
readers = {
    'csv': pd.read_csv,
    'xlsx': pd.read_excel,
    'json': pd.read_json,
    'txt': pd.read_csv,  # Assuming .txt is in a CSV-like format
    'parquet': pd.read_parquet,
    'hdf': pd.read_hdf,
    'feather': pd.read_feather,
    'sql': pd.read_sql,  # Requires a SQLAlchemy engine
}

# Determine the file extension
file_extension = file_path.split('.')[-1]

# Read the dataset dynamically
try:
    if file_extension in readers:
        if file_extension == 'sql':
            print("Reading from SQL databases requires a connection string. Please modify the code to provide it.")
            exit()
        else:
            # Try reading with utf-8 first, if it fails, catch the exception and try with a different encoding
            try:
                df = readers[file_extension](file_path)
            except UnicodeDecodeError:
                #print("UTF-8 decoding failed, trying ISO-8859-1 encoding.")
                df = readers[file_extension](file_path, encoding='ISO-8859-1')
    else:
        print("Unsupported file format. Please provide a valid dataset file.")
        exit()
except Exception as e:
    print(f"An error occurred: {e}")
    exit()

# Your existing content
content = (
    "Analyze the given dataset. The first line is header,"
    "and the subsequent lines are sample data,"
    "Columns may have unclean data in them. Ignore the cells,"
    "infer the data type by considering majority of the values in each column."
    "Supported types are 'string','integer','datetime','boolean','float'"
)

# API Details
url = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
model = "gpt-4o-mini"
headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

#This function will give us the idea of the dataset columns
functions = [
    {
        "name": "get_column_type",
        "description": "Identify column names and their data types from a dataset",
        "parameters": {
            "type": "object",
            "properties": {
                "column_metadata": {
                    "type": "array",
                    "description": "Metadata for each column.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "column_name": {
                                "type": "string",
                                "description": "Name of the column."
                            },
                            "column_type": {
                                "type": "string",
                                "description": "The data type of the column (e.g., integer, string)."
                            }
                        },
                        "required": ["column_name", "column_type"]
                    },
                    "minItems": 1
                }
            },
            "required": ["column_metadata"]
        }
    }
]

# Summary of the dataset
data_description = f"The dataset contains {df.shape[0]} records and {df.shape[1]} columns. The columns include {', '.join(df.columns)}."
analysis_description = "We performed an analysis of numerical and categorical data types, calculating key statistics like mean, median, and frequency distributions."
insights = "We found that certain columns showed significant variation in numerical values, while categorical columns indicated popular categories."
implications = "Based on these insights, we recommend focusing on the most common categories for targeted marketing and further investigating numerical anomalies for business strategy."

# Prepare README content
readme_content = f"# Dataset Summary\n\n## Data Description\n{data_description}\n\n## Analysis\n{analysis_description}\n\n## Insights\n{insights}\n\n## Implications\n{implications}\n"

# Save README.md
with open('README.md', 'w') as readme_file:
    readme_file.write(readme_content)

# Generate summary
summary = []

# Process numerical columns
numerical_columns = df.select_dtypes(include=['int64', 'float64']).columns
for col in numerical_columns:
    col_summary = {
        'Column Name': col,
        'Type': 'Numerical',
        'Mean': df[col].mean(),
        'Median': df[col].median(),
        'Standard Deviation': df[col].std(),
        'Min': df[col].min(),
        'Max': df[col].max(),
    }
    summary.append(col_summary)

# Process categorical columns
categorical_columns = df.select_dtypes(include=['object']).columns
for col in categorical_columns:
    col_summary = {
        'Column Name': col,
        'Type': 'Categorical',
        'Unique Values': df[col].nunique(),
        'Most Common Value': df[col].mode().iloc[0] if not df[col].mode().empty else 'N/A',
        'Missing Values': df[col].isnull().sum(),
    }
    summary.append(col_summary)

# Convert summary to a DataFrame for easy export
summary_df = pd.DataFrame(summary)

# Function to intelligently select meaningful columns
def select_meaningful_columns(df):
    numerical_columns = df.select_dtypes(include=['int64', 'float64']).columns
    categorical_columns = df.select_dtypes(include=['object']).columns

    # Exclude common identifiers like ID, ISBN, or codes
    excluded_columns = ['id', 'ID', 'isbn', 'ISBN', 'code', 'Code', 'index']
    numerical_columns = [col for col in numerical_columns if col.lower() not in excluded_columns]
    categorical_columns = [col for col in categorical_columns if col.lower() not in excluded_columns]

    # Select key numerical column: Highest variance, excluding trivial columns
    if numerical_columns:
        key_numerical_column = df[numerical_columns].var().idxmax()
    else:
        key_numerical_column = None

    # Select key categorical column: Most unique values, excluding trivial columns
    if categorical_columns:
        key_categorical_column = df[categorical_columns].nunique().idxmax()
    else:
        key_categorical_column = None

    return key_numerical_column, key_categorical_column

# Select meaningful columns
key_numerical_column, key_categorical_column = select_meaningful_columns(df)

# Create a 2x2 layout for the visualizations
fig, axs = plt.subplots(2, 2, figsize=(12, 10))

# Visualization 1: Histogram for the key numerical column (top left)
if key_numerical_column:
    sns.histplot(df[key_numerical_column], kde=True, color='blue', bins=20, ax=axs[0, 0])
    axs[0, 0].set_title(f'Distribution of {key_numerical_column}')
    axs[0, 0].set_xlabel(key_numerical_column)
    axs[0, 0].set_ylabel('Frequency')
else:
    axs[0, 0].set_visible(False)  # Hide the subplot if no meaningful numerical column is found

# Visualization 2: Bar chart for the key categorical column (top right)
if key_categorical_column:
    df[key_categorical_column].value_counts().head(10).plot(kind='bar', color='orange', ax=axs[0, 1])
    axs[0, 1].set_title(f'Top Values in {key_categorical_column}')
    axs[0, 1].set_ylabel('Frequency')
    axs[0, 1].set_xlabel(key_categorical_column)
else:
    axs[0, 1].set_visible(False)  # Hide the subplot if no meaningful categorical column is found

# Visualization 3: Correlation heatmap for numerical columns (bottom left)
numerical_columns = df.select_dtypes(include=['int64', 'float64']).columns
correlation_matrix = df[numerical_columns].corr()
if not correlation_matrix.empty:
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', ax=axs[1, 0])
    axs[1, 0].set_title('Correlation Heatmap')
else:
    axs[1, 0].set_visible(False)  # Hide the subplot if correlation is not meaningful

# Remove the unused subplot for a cleaner layout (bottom right)
axs[1, 1].remove()  # Bottom-right subplot removed for balance

# Adjust layout
plt.tight_layout()
plt.savefig("images.png", dpi=100, bbox_inches='tight')
plt.close()
print("All visualizations saved in 'images.png'.")

# Prepare dynamic prompt for README content
data_description = f"The dataset contains **{df.shape[0]}** records and **{df.shape[1]}** columns. The columns include:\n- {', '.join(df.columns)}.\n"

# Collect insights from numerical columns
numerical_insights = []
for col in numerical_columns:
    mean_val = df[col].mean()
    median_val = df[col].median()
    std_dev = df[col].std()
    numerical_insights.append(
        f"The column **{col}** has a mean value of **{mean_val:.2f}**, a median of **{median_val:.2f}**, "
        f"and a standard deviation of **{std_dev:.2f}**. This indicates significant variability in the data."
    )

# Collect insights from categorical columns
categorical_insights = []
for col in categorical_columns:
    unique_count = df[col].nunique()
    most_common = df[col].mode().iloc[0] if not df[col].mode().empty else 'N/A'
    categorical_insights.append(
        f"The column **{col}** contains **{unique_count}** unique values, with **{most_common}** being the most common value."
    )

# Combine all insights
insights = "\n".join(numerical_insights + categorical_insights)

# Prepare the full README content
readme_content = (
    "# Dataset Summary\n\n"
    "## Data Description\n"
    f"{data_description}\n"
    "This dataset provides insights into various factors that may impact decisions related to the data at hand.\n\n"
    
    "## Analysis\n"
    "We conducted a thorough analysis of both numerical and categorical data types, focusing on key statistics such as mean, median, standard deviation, and frequency distributions.\n\n"
    
    "## Insights\n"
    f"We discovered the following insights:\n{insights}\n\n"
    
    "## Implications\n"
    "The insights drawn from this analysis highlight important trends and variations in the data. Based on these findings, we recommend:\n"
    "- Targeted Marketing: Focus on prominent categories and values to optimize marketing strategies.\n"
    "- Further Investigation: Explore numerical anomalies to identify potential opportunities or issues.\n"
    "- Strategic Decisions: Use the insights on popular values to guide business strategy and positioning.\n\n"
    
    "By leveraging these findings, stakeholders can make informed decisions to enhance their offerings and better meet the needs of their audience.\n\n"
    
    "## Summary Statistics\n"
    f"{summary_df.to_markdown(index=False)}"
)

# Save README.md
with open('README.md', 'w') as readme_file:
    readme_file.write(readme_content)

print("Summary saved to README.md")

# Prepare data for API request visualizations

data = f"The dataset consists of {df.shape[0]} records and {df.shape[1]} columns: {', '.join(df.columns)}."

# Prepare API request
json_data = {
    "model": model,
    "messages": [
        {"role": "system", "content": content},
        {"role": "user", "content": data}
    ],
    "functions": functions,
    "function_call": {"name": "get_column_type"}
}

# Send request
r = requests.post(url=url, headers=headers, json=json_data)
metadata = json.loads(r.json()['choices'][0]['message']['function_call']['arguments'])['column_metadata']
