import json
from typing import Tuple

from pyflink.common import SimpleStringSchema, WatermarkStrategy, Types, Time, Row
from pyflink.datastream import StreamExecutionEnvironment, MapFunction, AggregateFunction
from pyflink.datastream.connectors.kafka import KafkaSource, KafkaOffsetsInitializer, KafkaSink, \
    KafkaRecordSerializationSchema
from pyflink.datastream.formats.json import JsonRowSerializationSchema
from pyflink.datastream.window import TumblingEventTimeWindows

from pyflink.table import *
from pyflink.table.expressions import call, col, lit
from pyflink.table.window import Tumble

def process_json_data():
    env = StreamExecutionEnvironment.get_execution_environment()
    t_env = StreamTableEnvironment.create(stream_execution_environment=env)
    t_env.get_config().get_configuration().set_boolean("python.fn-execution.memory.managed", True)

    create_kafka_source_ddl = """
            CREATE TABLE iot_msg(
                client VARCHAR,
                ts TIMESTAMP(3),
                temperature DOUBLE,
                humidity DOUBLE,
                WATERMARK FOR ts AS ts - INTERVAL '5' SECOND
            ) WITH (
              'connector' = 'kafka',
              'topic' = 'weather_data',
              'properties.bootstrap.servers' = 'kafka:9092',
              'properties.group.id' = 'test_3',
              'scan.startup.mode' = 'latest-offset',
              'format' = 'json'
            )
            """

    create_es_sink_ddl = """
            CREATE TABLE es_sink(
                client VARCHAR PRIMARY KEY NOT ENFORCED,
                row_date DATE,
                row_time TIME(0),
                avg_temp DOUBLE,
                avg_hum DOUBLE
            ) with (
                'connector' = 'elasticsearch-7',
                'hosts' = 'http://elasticsearch:9200',
                'index' = 'weather_data_1',
                'document-id.key-delimiter' = '$',
                'sink.bulk-flush.max-size' = '42mb',
                'sink.bulk-flush.max-actions' = '32',
                'sink.bulk-flush.interval' = '1000',
                'sink.bulk-flush.backoff.delay' = '1000',
                'format' = 'json'
            )
    """

    t_env.execute_sql(create_kafka_source_ddl)
    t_env.execute_sql(create_es_sink_ddl)

    iot_data = t_env.from_path("iot_msg") 

    results = iot_data.window(Tumble.over(lit(1).minutes).on(col("ts")).alias("w")) \
        .group_by(col("w"), col("client")) \
        .select(col("client"), col("w").rowtime.to_date.alias("row_date"), col("w").rowtime.to_time.alias("row_time"), col("temperature").avg.alias("avg_temp"), col("humidity").avg.alias("avg_hum")) \
        .execute_insert("es_sink")


if __name__ == '__main__':
    process_json_data()