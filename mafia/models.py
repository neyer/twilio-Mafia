from django.db import models

# Create your models here.




class Game(models.Model):

    STATE_SETUP = 0
    STATE_PLAYING = 1
    STATE_FINISHED = 2

    "Represents a single game of mafia."

    name = models.CharField(max_length=32,
                            unique=True,
                            db_index =True)

    state = models.IntegerField(default=STATE_SETUP)


    def get_players(self):
        return Player.objects.filter(game=self)


    def start(self):
        "starts the game, telling each player his role."
        


class Player(models.Model):
    
    phone_num = models.CharField(max_length=64,
                                 unique=True,
                                 db_index=True)

    short_name = models.CharField(max_length=64)

    game = models.ForeignKey(Game,db_index=True)

    

    
