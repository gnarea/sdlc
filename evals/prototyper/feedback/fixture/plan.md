# Appointment-reminders prototype plan

Missed appointments cost an independent dental practice about £500 a week in empty chair time. We want to sell practices a service that sends patients a reminder by text message two days before each appointment, and lets them confirm or cancel by replying. The prototype tests whether practices would pay for it, and whether it can work with the practice-management system that most of them use.

## Questions

### Would practice managers pay £40 a month for the service?

- **Risk**: The business case depends on it. Below £40 a month per practice, the service won't cover the cost of the text messages and of support, and we won't build it.
- **Approach**: Show a clickable mock-up of the service and its pricing page to 12 practice managers from the regional dental association, who've agreed to take part. Ask each one to sign a letter of intent to subscribe at £40 a month once the service launches, with the first three months free.

### Can we read each practice's upcoming appointments from its practice-management system?

- **Risk**: Without the appointments, there's nothing to remind patients of. If the system's API can't provide them, practices would have to export their diary every day, which few would do, and we'd drop the project.
- **Approach**: Hypothesis: the practice-management system's API returns every appointment booked for the coming week. Test: book 30 test appointments in the training diary of each of the two practices taking part, and fetch the coming week's appointments through the API.

### Can patients confirm or cancel by replying to the reminder?

- **Risk**: Patients ignore reminders they can't reply to, so a one-way reminder would save practices far fewer appointments, and justify a lower price.
- **Approach**: Hypothesis: the text-message provider passes each reply to our service within 60 seconds, and the practice-management system's API accepts the cancellations. Test: send 50 reminders to the team's own phones, for test appointments in the two practices' training diaries, and reply to each one. Refuted if any reply takes longer than 60 seconds to reach our service, or if the API rejects any cancellation.

## Non-goals

- Reminders by email or post: practices already send them.

## Compromises

- **Made-up patients**: The mock-up shows made-up patients and appointments, since practice managers only need to see what the service would do.
