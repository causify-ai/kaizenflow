import argparse
import logging
import sys

from pyflink.table import TableEnvironment, EnvironmentSettings, TableDescriptor, Schema,\
    DataTypes, FormatDescriptor
from pyflink.table.expressions import col, lit
from pyflink.table.udf import udf

# Define a list of words to be used in the data generation.
words = ["flink", "window", "timer", "event_time", "processing_time", "state",
         "connector", "pyflink", "checkpoint", "watermark", "sideoutput", "sql",
         "datastream", "broadcast", "asyncio", "catalog", "batch", "streaming"]

# Calculate the maximum index for word selection.
max_word_id = len(words) - 1

def streaming_word_count(output_path):
    """
    Configures and executes a Flink streaming job that counts occurrences of words.
    
    Args:
    output_path (str): Path to the output directory where results will be saved.
                       If None, outputs to standard output.
    """
    # Initialize a TableEnvironment in streaming mode.
    t_env = TableEnvironment.create(EnvironmentSettings.in_streaming_mode())

    # Set up a source table that generates random word IDs.
    t_env.create_temporary_table(
        'source',
        TableDescriptor.for_connector('datagen')
                       .schema(Schema.new_builder()
                               .column('word_id', DataTypes.INT())
                               .build())
                       .option('fields.word_id.kind', 'random')
                       .option('fields.word_id.min', '0')
                       .option('fields.word_id.max', str(max_word_id))
                       .option('rows-per-second', '5')
                       .build())
    # Retrieve the dynamically generated table.
    tab = t_env.from_path('source')

    # Set up a sink for the results based on the provided output path.
    if output_path is not None:
        t_env.create_temporary_table(
            'sink',
            TableDescriptor.for_connector('filesystem')
                           .schema(Schema.new_builder()
                                   .column('word', DataTypes.STRING())
                                   .column('count', DataTypes.BIGINT())
                                   .build())
                           .option('path', output_path)
                           .format(FormatDescriptor.for_format('canal-json')
                                   .build())
                           .build())
    else:
        print("Printing result to stdout. Use --output to specify output path.")
        t_env.create_temporary_table(
            'sink',
            TableDescriptor.for_connector('print')
                           .schema(Schema.new_builder()
                                   .column('word', DataTypes.STRING())
                                   .column('count', DataTypes.BIGINT())
                                   .build())
                           .build())

    # Define a user-defined function to convert word IDs back to words.
    @udf(result_type='string')
    def id_to_word(word_id):
        """Converts a word_id to a word using a predefined list of words."""
        return words[word_id]

    # Perform the word count using the defined UDF and insert the results into the sink.
    tab.select(id_to_word(col('word_id')).alias('word')) \
       .group_by(col('word')) \
       .select(col('word'), lit(1).count.alias('count')) \
       .execute_insert('sink') \
       .wait()  # This wait() call blocks until the job is finished (useful for batch-like jobs).

if __name__ == '__main__':
    # Set up logging to display info level logs on the console.
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(message)s")

    # Configure argument parsing to handle the output path via command line.
    parser = argparse.ArgumentParser(description="Run a Flink word count streaming job.")
    parser.add_argument('--output', dest='output', required=False, help='Output file to write results to.')

    # Parse known arguments.
    known_args, _ = parser.parse_known_args(sys.argv[1:])

    # Run the main function with the specified output path.
    streaming_word_count(known_args.output)
