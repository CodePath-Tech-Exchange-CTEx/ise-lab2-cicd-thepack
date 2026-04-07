# Usability Test Writeup
**Team:** Susana, Tesfa, Nishan
**Features Tested:** Feature 1 – Adaptive Fitness Plan | Feature 2 – Social Challenges

---


## Tasks

### Feature 1 – Adaptive Fitness Plan

**Task 1:**
"You just downloaded a new fitness app and want to get a personalized workout plan set up for yourself. Go ahead and do that."

**Task 2:**
"It's Monday. You want to see what workout you are supposed to do today and get started."

### Feature 2 – Social Challenges

**Task 3:**
"You heard there is a step challenge happening in the app that some people have already joined. You want to take part in it."

**Task 4:**
"You have been doing the challenge for a few days and want to check how you are doing compared to everyone else."

---

## Notes

### Participant 1

- Navigated to the Plan tab without hesitation and selected "Fitness Plan" quickly.
- On the Goal Setup screen, paused for several seconds in front of the three blank input boxes. Hovered over them unsure of what information to enter. Said "I'm not sure what this is asking me."
- Filled in the Experience Level and Activity Level sections without much trouble after some exploration.
- On the weekly schedule screen, scrolled up and down looking at the list of days but did not tap any of them. Waited for about 15 seconds then said "I think I'm done? I don't know if there's more."
- Did not discover the workout detail screen (Upper Body / exercises list) on their own.
- For Feature 2, navigated to the Community tab and found the challenge list quickly.
- On the progress screen, glanced at the days tracker and the leaderboard button but scrolled past the leaderboard
- 
### Participant 2

- Also paused at the Goal Setup form. Said "Are these for my name or like my weight or what?"
- Completed the experience and activity level selection confidently.
- On the weekly schedule, tapped MON – Upper Body after a moment of hesitation. Successfully reached the workout detail screen.
- Said "Oh okay so it does go somewhere, I wasn't sure if I was supposed to press it."
- After marking the workout complete, said "Is that it?"
- For Feature 2, found the challenge and read the detail screen carefully.
- On the progress screen, said "Why does it show the days again? I already saw this."
- Did not interact with the leaderboard button without being prompted.

---

## Feedback

### Participant 1

**Q: How easy or hard was it to set up your fitness plan?**
A: "Pretty easy once I figured out what the boxes were for. I just didn't know what to type at first."

**Q: What confused you about the weekly schedule screen?**
A: "I didn't know you could press the days. It just looked like a list to me. Nothing told me to tap it."

**Q: For the challenge feature, what was confusing about the buttons?**
A: "The two buttons looked the same size and color, so I just guessed."

**Q: What could be improved overall?**
A: "Label the input fields so I know what to put. And maybe make the days look more like buttons. Also some kind of finish screen would be nice."

### Participant 2

**Q: What was your first reaction to the Goal Setup screen?**
A: "I was like, okay, what is this asking me? Are these for my name or like my weight or what?"

**Q: After completing the workout, how did you feel about the experience?**
A: "Is that it? I kind of expected like a congrats screen or something, like a streak."

**Q: What did you think of the days tracker appearing twice in the challenge feature?**
A: "Why does it show the days again? I already saw this."

**Q: Was there anything you wish was more visible?**
A: "The leaderboard thing i would have not pressed it."

---

## Results

### Issue 1 – Goal Setup fields had no labels
**Hypothesis:** The three input boxes were rendered as blank rectangles with no placeholder text or field labels, giving users no context for what information was expected.
**Participant quote:** "I'm not sure what this is asking me."
**Remedy:** Add visible labels above or inside each input field

### Issue 2 – Weekly schedule days did not appear tappable
**Hypothesis:** The day rows on the weekly schedule looked like a static list. 
**Participant quote:** "Oh okay so it does go somewhere, I wasn't sure if I was supposed to press it."
**Remedy:** Add a visible "›" arrow on the right side of each day row to signal that it is tappable and leads to more content.

### Issue 3 – No completion/feedback screen after finishing a workout
**Hypothesis:** After tapping "Mark as complete," the flow ended abruptly with no confirmation, leaving users uncertain whether their action was registered and feeling like something was missing.
**Participant quote:** "Is that it? I kind of expected like a streak."
**Remedy:** Add a Workout Complete screen with a summary 

### Issue 5 – Duplicate days tracker on the pre-join screen was ignored
**Hypothesis:** The "Progress Preview" showing 0/30 days before the user had joined the challenge felt meaningless and out of place, causing users to skip past it.
**Participant quote:** "Why does it show the days again? I already saw this."
**Remedy:** Remove the Progress Preview section from the pre-join screen. Only display the days tracker on the active progress screen after the user has joined.

### Issue 6 – Leaderboard button was not visible enough
**Hypothesis:** The "CHECK LEADERBOARD" button was placed at the bottom of the progress screen below other content, making it easy to miss during natural scrolling.
**Participant quote:** "The leaderboard thing should be bigger or higher up"
**Remedy:** Move the leaderboard button
