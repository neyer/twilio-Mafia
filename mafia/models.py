from django.db import models
import random
# Create your models here.



#game states
STATE_SETUP = 1
STATE_PLAYING = STATE_SETUP+1
STATE_FINISHED = STATE_PLAYING+1

MAFIA_FRACTION = 0.3

#teams
TOWN = 1
MAFIA = 2

class Game(models.Model):
    "Represents a single game of mafia."


    name = models.CharField(max_length=32,
                            unique=True,
                            db_index =True)
    password = models.CharField(max_length=32)	

    state = models.IntegerField(default=STATE_SETUP)


    def get_players(self):
        return Player.objects.filter(game=self).filter(alive=True)

    def get_team(self, for_team):
        return self.get_players().filter(team=for_team).filter(alive=True)


    def start(self):
	"starts the game, telling each player his role."
        players = self.get_players()
        num_players = len(players)
        num_mafia = num_players*MAFIA_FRACTION

        unassigned = [player for player in players]
        random.shuffle(unassigned)

        i = 0
        for player in unassigned:
            if i >= num_mafia:
                player.assign_team(TOWN)
            else:
                player.assign_team(MAFIA)
            i += 1

        
        self.state = STATE_PLAYING
        self.save()

        
    def check_votes(self):
        "Checks all votes to determine wether a kill should occur."
        players = self.get_players()
        
        #initialize an empty vote count for each side
        town_voters = self.get_team(TOWN).filter(alive=True)
        mafia_voters = self.get_team(MAFIA).filter(alive=True)
        
        town_votes_needed = int(1+(len(players)/2.0))

        self.check_for_kill(town_voters, town_votes_needed, TOWN)
        self.check_for_kill(mafia_voters, len(mafia_voters), MAFIA)



    def check_for_kill(self, voters, votes_needed, killing_team):
        "Determines if the given set of voters has enough votes "\
        "to kill their target."

        votes = {}
        for player in self.get_players():
            votes[player] = 0

        for voter in voters:
            if voter.target and voter.target.alive:
                votes[voter.target] += 1

        for victim in votes:
            if victim.alive and votes[victim] >= votes_needed:
                self.kill(victim,killing_team)
                return

    def kill(self, victim, killing_team):
        victim.die()        

        winner = self.check_for_victory()
        if winner:
            self.state = STATE_FINISHED
            self.save()

    def check_for_victory(self):
        townspeople = self.get_team(TOWN).filter(alive=True)
        mafia = self.get_team(MAFIA).filter(alive=True)
        
	#print "There are %d mafia players left." % len(mafia)
        if len(mafia) >= len(townspeople):
            return MAFIA
        elif len(mafia) == 0:
            return TOWN
	return None 



class Player(models.Model):
    
    phone_num = models.CharField(max_length=64,
                                 unique=True,
                                 db_index=True)

    name = models.CharField(max_length=64)

    game = models.ForeignKey(Game,db_index=True)
    is_admin = models.BooleanField(default=False)



    #game specific fields
    team = models.IntegerField(default=-1)

    target = models.ForeignKey("Player",
                               null=True,
                               default=None)

    alive = models.BooleanField(default=True)

    def assign_team(self, team):
        self.team = team
        self.save()

    def die(self):
	self.alive = False
	self.save()

	
#an abstract base class for all player performed actions
class Action(models.Model):
    player = models.ForeignKey(Player)
    timestamp = models.DateTimeField(auto_now_add=True)


#the player votes for another 
class Vote(Action):
    target = models.ForeignKey(Player)

    def process(self):
        "Causes the action to play itself out"
	#print "%s voted for %s" % (self.player.name,
	#			   self.target.name)
        self.player.target = self.target
        self.player.save()
        self.player.game.check_votes()



###########################################
 #messaging
 #outgoing message classes are created for each message
 #so the game can keep track of which messages it sends to players
 #and to make testing eaiser
###########################################
class OutgoingMessage(models.Model):
    body = models.CharField(max_length=128)
    from_number = models.CharField(max_length=32)
    to_number  = models.CharField(max_length=32)
        
    
    #eventually we'll define a send function for this guy
