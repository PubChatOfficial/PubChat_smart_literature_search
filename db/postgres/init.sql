--
-- PostgreSQL database dump
--

\restrict 5oBJiwXN9eNJzbVOhi3JAhpNyntzPg3x90BAC8HX2lFPT8dtOyxrUPbbdWnVbtD

-- Dumped from database version 15.15
-- Dumped by pg_dump version 15.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

CREATE SCHEMA IF NOT EXISTS "userSchema";

CREATE TABLE "userSchema".documents (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	task_id uuid NOT NULL,
	"size" float4 NULL,
	user_query varchar NULL,
	created_time timestamptz NULL,
	download_link varchar NULL,
	CONSTRAINT documents_pk PRIMARY KEY (id)
);


-- "userSchema".tasks definition

-- Drop table

-- DROP TABLE "userSchema".tasks;

CREATE TABLE "userSchema".tasks (
	id uuid DEFAULT gen_random_uuid() NOT NULL,
	output_language varchar DEFAULT '"zh"'::character varying NULL,
	user_query varchar NULL,
	max_refinement_attempts int4 NULL,
	min_study_threshold int4 NULL,
	"time" varchar NULL,
	author varchar NULL,
	first_author varchar NULL,
	last_author varchar NULL,
	affiliation varchar NULL,
	journal varchar NULL,
	custom varchar NULL,
	impact_factor varchar NULL,
	jcr_zone varchar NULL,
	cas_zone varchar NULL,
	create_time timestamptz DEFAULT now() NULL,
	status varchar DEFAULT 'pending'::character varying NULL,
	model varchar NULL,
	api _text NULL,
	pubmed_api _text NULL,
	CONSTRAINT tasks_pk PRIMARY KEY (id)
);


-- "userSchema".documents foreign keys

ALTER TABLE "userSchema".documents ADD CONSTRAINT documents_tasks_fk FOREIGN KEY (task_id) REFERENCES "userSchema".tasks(id) ON DELETE CASCADE ON UPDATE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict 5oBJiwXN9eNJzbVOhi3JAhpNyntzPg3x90BAC8HX2lFPT8dtOyxrUPbbdWnVbtD
