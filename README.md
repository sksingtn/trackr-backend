<img src="https://raw.githubusercontent.com/FortAwesome/Font-Awesome/d3a7818c253fcbafff9ebd1d4abb2866c192e1d7/svgs/solid/calendar-week.svg"  width="50" height="50"> 

This is the backend(Django) repository for trackr.\
For the frontend(ReactJS) repository, click [here](https://github.com/sksingtn/trackr-frontend "here")

# Trackr

Trackr is a SPA web application built with Django & ReactJS which can be used by faculty & students of any organisation to efficiently manage their classes in one place. Basically it can be used anywhere where a weekly routine is followed.

Trackr provides the following 3 roles:

- **ADMIN** - Admins can create and manage batches & the individual slots inside them as well as invite,manage & broadcast messages to their student & faculties.

- **FACULTY** - Faculties can track the weekly classes assigned to them to teach as well as get notified for the same if opted for.They can also broadcast messages to their students.

- **STUDENT** -  Students can track the weekly classes assigned to them to attend as well as get notified for the same if opted for.They can also view messages from their faculty & admin.


# Overview

 - **Admin Dashboard**  
 
 [![admin-dashboard.png](https://i.imgur.com/OaVyj9r.png)](https://i.imgur.com/OaVyj9r.png)
 
 Admins can create/update/delete slots in all the batches that were created by them. They can simply add a faculty profile
 as a placeholder or they can link their email & invite them to create an account & track their classes.
 
 Students can be invited via a invite link that is unique for every batch & accessible to admin. They can also control the 
max size of the batch and pause the batch when needed.

- **Faculty & Student Dashboard**

 [![common-dashboard.png](https://i.imgur.com/gmhABT8.png)](https://i.imgur.com/gmhABT8.png)

 Students & Faculties can quickly see their upcoming, ongoing & previous classes. Rest of the classes are grouped by weekday
 and are visible in the caraousel.

 # Built with
 - ReactJS
 - Redux Toolkit
 - Material UI
 - Styled Components
 - Django
 - Django Rest Framework
 - Redis (notification for upcoming classes)

