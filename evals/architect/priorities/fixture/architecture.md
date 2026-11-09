# Box office

The box office system sells tickets for the Northgate Playhouse's performances, online and at the box office counter. It holds the seating plan of each performance, takes payments through our card processor, and emails each customer their tickets.

## Purpose

Customers need to book seats without being sold one that someone else already has, and to keep their seats once they've paid. Most of a season's tickets sell in the first hours after the season goes on sale, at a time that we announce weeks ahead.

Non-goals:

- Selling tickets for other venues.
- Storing card details: the card processor holds them, and we only keep its payment references.

### Users and other stakeholders

- **Customers**: Book online, or in person at the counter. About 2,000 book in the first hour of a season's sale, and a few hundred a day after that.
- **Box office staff**: Sell tickets at the counter, change bookings, and issue refunds.
- **Operators**: One contractor, who is on call on the days a season goes on sale.

## Principles

### A confirmed booking is never lost

A customer who has paid for a seat keeps it, whatever fails. This favours durability over cost.

### Sales survive the loss of a server or an availability zone

An outage at the start of a sale loses sales to resellers, and fills the foyer with angry customers. Sales must resume within two minutes of losing the database's instance or its availability zone, at the expense of paying for a standby.

## Components

- **Web app**: Serves the online shop and the box office counter, as a container on Amazon ECS in two availability zones, behind an Application Load Balancer.
- **Database**: Amazon RDS for PostgreSQL, on a `db.r6g.xlarge` instance, sized for the start of a sale. It holds the seating plans, the bookings, customers' names and email addresses, and the card processor's payment references.
  - It's a Multi-AZ deployment: a synchronous standby replica in a second availability zone takes over within about two minutes if the primary fails.
  - It has automated backups with 14 days of point-in-time recovery, and a monthly snapshot that's kept for a year. We test a restore every quarter.
  - Customers' details are deleted 3 years after their last booking.

## Running costs

The system costs about $900 a month:

- The database: $780, of which $360 is the primary, $360 the standby, and $60 the backup storage.
- Everything else: $120.
