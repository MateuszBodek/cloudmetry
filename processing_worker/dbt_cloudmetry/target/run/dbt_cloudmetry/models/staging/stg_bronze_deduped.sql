
  
  create view "memory"."main"."stg_bronze_deduped__dbt_tmp" as (
    

SELECT DISTINCT ON (vehicle_id, drive_id, stream, source_time_s)
    vehicle_id,
    drive_id,
    stream,
    source_time_s,
    sampled_at,
    generated_at,
    data_json,
    filename AS source_file
FROM read_parquet(
    ['s3://bronze/telemetry/1793401552-12731280-9595-48bc-859e-eb29d6e256c7.parquet', 's3://bronze/telemetry/1793401582-891c511e-43a6-4fb6-9e30-ec2f7efb107d.parquet', 's3://bronze/telemetry/1793401612-ba39ea7a-cbb6-4314-9147-4ec5dc13bcfb.parquet', 's3://bronze/telemetry/1793401642-46ee2b94-1d44-4527-b663-4a63683e39d3.parquet', 's3://bronze/telemetry/1793401672-3c3bbe69-f5ab-4547-a915-66c9a10670e4.parquet', 's3://bronze/telemetry/1793401702-733b16a7-5cb4-4c9f-9503-ddd79733a8a0.parquet', 's3://bronze/telemetry/1793401732-28493303-63cf-44e6-b455-f6a7082d9ab3.parquet', 's3://bronze/telemetry/1793401762-00ad7dc6-c485-410d-97c7-16e4551eaad2.parquet', 's3://bronze/telemetry/1793401792-1720ed2d-84c9-4d70-9852-7abd875154ad.parquet', 's3://bronze/telemetry/1793401822-06cf9026-0a11-47d8-9eef-b56227b2382c.parquet', 's3://bronze/telemetry/1793401852-77e56653-877f-4279-830d-63716b87f9a6.parquet', 's3://bronze/telemetry/1793401882-a10da46d-bb6b-44cc-b80f-7a3a6a9d3d84.parquet', 's3://bronze/telemetry/1793401912-1d570fd3-b783-48a4-b0e3-c5e9c351e488.parquet', 's3://bronze/telemetry/1793401942-acc815dd-9a36-4828-84e3-b8f3448f3d0e.parquet', 's3://bronze/telemetry/1793401972-02de79b4-c4a3-46a2-9b16-1a71a19c0b76.parquet', 's3://bronze/telemetry/1793402002-7944debc-b482-43af-a927-f54fbaa19cf5.parquet', 's3://bronze/telemetry/1793402032-74157520-034c-4381-921f-4748a0e0cd1d.parquet', 's3://bronze/telemetry/1793402062-b6530594-9b7f-4712-a467-086ccc6de391.parquet', 's3://bronze/telemetry/1793402092-af35e47b-2fde-43b6-a07f-c363e4581ed4.parquet', 's3://bronze/telemetry/1793402122-d92e0e7b-1fca-437e-aa90-477ec473e76e.parquet', 's3://bronze/telemetry/1793402152-092f01b0-bc8b-43a1-b279-a22dbe0f99cf.parquet', 's3://bronze/telemetry/1793402182-42fdce1a-3850-448d-bd30-46c7f828848b.parquet', 's3://bronze/telemetry/1793402212-4b053539-162a-45d5-8b94-8342455f4336.parquet', 's3://bronze/telemetry/1793402242-90faf341-9c6f-474a-86f6-4282fc05df22.parquet', 's3://bronze/telemetry/1793402272-219457b8-99ee-4389-8f62-8cf92b466b39.parquet', 's3://bronze/telemetry/1793402302-07e7ced6-3847-4e7d-a533-5fcaeb868075.parquet', 's3://bronze/telemetry/1793402332-553057e1-6473-4f1c-b294-319691960f89.parquet', 's3://bronze/telemetry/1793402362-360b469c-3fac-497c-a2d8-521f5f9117c2.parquet', 's3://bronze/telemetry/1793402392-16d49fcc-2f3c-4015-bed1-0a1a10f89689.parquet', 's3://bronze/telemetry/1793402421-0966f0e7-c055-48de-8cd5-f1e34997593c.parquet', 's3://bronze/telemetry/1793402452-3d7bf470-d7c7-4633-91c9-fcfc6ef88f4e.parquet', 's3://bronze/telemetry/1793402482-f50e52b7-0d99-457b-892d-de579b6b5fd7.parquet', 's3://bronze/telemetry/1793402512-ef455367-fafd-4e0a-9a72-be9fdfe204c8.parquet', 's3://bronze/telemetry/1793402541-c2339e37-dc06-4120-9a87-e33745f6c39c.parquet', 's3://bronze/telemetry/1793402571-62e8a8cb-4847-4744-a676-ddc0e161f7ee.parquet', 's3://bronze/telemetry/1793402601-39f80773-be17-4e83-9827-574231132f86.parquet', 's3://bronze/telemetry/1793402631-54bc036d-7bc5-4cef-9b2f-4dc117969c41.parquet', 's3://bronze/telemetry/1793402661-d6d50590-0e69-4a98-975b-299c5024c051.parquet', 's3://bronze/telemetry/1793402691-975b375e-496b-4403-91cc-b6c0eb9860d2.parquet'],
    filename = true,
    union_by_name = true
)
ORDER BY
    vehicle_id,
    drive_id,
    stream,
    source_time_s,
    TRY_CAST(generated_at AS TIMESTAMP) DESC NULLS LAST,
    filename DESC
  );
