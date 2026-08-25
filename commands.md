# Common Commands

## Start everything
docker compose up

## Stop everything
docker compose down

## See what's running
docker ps

## Look inside the database via terminal
docker exec -it be-a1-first-crud-api-db-1 psql -U postgres -d tasks

## then inside the terminal after runinng above command to see the whole table
SELECT * FROM tasks;

# then for getting exit
\q


## Command to start docker desktop
systemctl --user start docker-desktop

## Command to stop docker desktop
systemctl --user stop docker-desktop

## Wait a bit (because VM(virtual machine) takes time to boot):
sleep 15

## to confirm the status
systemctl --user status docker-desktop

## It should appear active (running). Press 'q' after viewing to exit the page.

## Open a new terminal (the old session doesn't recognize the new socket — remember this pattern):

docker ps

# if empty table shows means docker is ready

# then inside the folder
docker compose up 