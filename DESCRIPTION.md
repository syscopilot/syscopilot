# syscopilot

# Core MVP
Helps you describe your system into a system format  
After the format is done, it gives you a senior system design feedback. 

## How
Given a system format and an empty result matching the format:  
The code asks the User some guiding questions  
```
While the result is not completed:
- The user starts to describe the system (by answering some of the questions),
- The AI model tries to take the description and put it into the result
- The AI model asks more guiding questions
```
The AI model, receives the result and gives a feedback.


## Things to figure out
**Q: How to put any given system into format?**  
*A: We need to seperate the systems into kinds. The MVP would only support data pipeline systems*  
*A: We need to come up with a format for Data Pipelines. It's a research*

## Todo
- [ ] come up with a format for data pipelines

## Next Ideas
* Visuallize the system
* Let the user descsribe the system, using a UI
* Crazy Idea: The user describes a system, and the application deploys it from scratch