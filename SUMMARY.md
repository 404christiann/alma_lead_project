# Take-Home Assignment Summary

## What to Build

Develop an application to support creating, getting, and updating leads. A lead is a form publicly available for prospects to fill in, requiring the following fields:
- First name
- Last name
- Email
- Resume / CV

## Inputs / Outputs

**Inputs:**
- Public form with fields: first name, last name, email, resume/CV

**Outputs:**
- Upon lead submission by a prospect, the application sends emails to both the prospect and an attorney inside the company
- Internal UI (guarded by authentication) that renders a list of leads with all information filled in by the prospect
- Each lead has a state that starts with **PENDING** and transitions to **REACHED_OUT** when marked manually by an attorney after they reach out to the prospect

## Constraints

- Create a system design to fulfill the requirements
- Develop the web app and APIs E2E using coding agents of your choice
- APIs must be implemented using FastAPI
- Web app must be built using NextJS
- Add a storage solution to persist data and integrate with an email service
- Properly structure the code similar to how you would for a production-level repository
- Submit code to a publicly available GitHub repository
- Submit a document on how to run your application locally in the same repository

## Edge Cases

- No specific edge cases are explicitly detailed in the assignment

## What Done Looks Like

- Functional system design documented
- E2E web application and APIs implemented (FastAPI for APIs, NextJS for web app)
- Data persistence layer integrated
- Email service integration working
- Code organized to production standards
- Public GitHub repository containing all code
- Documentation file explaining local setup and how to run the application
