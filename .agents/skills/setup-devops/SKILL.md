---
name: setup-project
description: Programming project setup, including language, package manager, containerization/deployment form, CICD pipeline, dependencies roster, observability frameworks 
---

# Programming project setup

## Init

Scan existing repository to find out setup aspects already evident/decided upon;
If not found, suggest options with pros, cons and tradeoffs explained.

## Language

## Package manager
Look up for best stable option on web

## Deployment form
For backend app, wrap with docker compose

## CICD pipeline
Setup initial GitHub/chosen provider repository if missing; Set up provider CICD script/configuration for build; to not attach deployment configuration, it is out of scope

## Dependencies
Repare roster of selected package management type; only populate it if there is dependency data in project sources/docs

## Observability
For backend app, attach Sentry.io dependency

## Generate DevOps doc

Record all decisions and setup form into docs/cicd.md

## README.md

If docs are sufficient, generate repository README.md with logo (if found), version/code/licence (MIT) tags;
With sections:
- What it is
- Setup
- Requirements
