from django.db import models
import random
from twilio_wrapper import *
# Create your models here.
from urllib import urlencode


#game states
STATE_SETUP = 1
STATE_PLAYING = STATE_SETUP+1
STATE_FINISHED = STATE_PLAYING+1

MAFIA_FRACTION = 0.3

#teams
TOWN = 1
MAFIA = 2

GAME_NUMBER = '5136731535'

INTRO_TEXTS = { TOWN : 'Hello. You are a part of the town. '\
			'You have heard rumors of mafia activity. '\
			'Your goal is to  identify the members of the mafia '\
			'and bring them to justice. You can text '\
			'vote name to cast your vote for the town to kill '\
			'name next. Good luck!'.replace(' ','%20'),

		MAFIA: 'Hello. You are a part of the mafia. '\
			'Your goal is to kill the town members one by one '\
			'until half the town is a mafia member.' \
			'You can text vote name to cast your vote '\
			'for name to be the next hit. If you need help '\
			'text help.'.replace(' ', '%20')
	    }

KILLED_TEXTS = { MAFIA : 'You have been accused by the town of mafiary '\
			'and are sentenced to die. Have a nice day.'.replace(' ','%20'),
		TOWN: 'You have been killed by the mafia. Have a nice day.'.replace(' ','%20')
	    }


VICTORY_TEXTS = { MAFIA : 'The mafia have taken over the town. May god have mercy on us all.',
		  TOWN : 'The town has killed off the mafia! Now we can sleep safe at night.'
		  }
TWIMLETS_BASE_URL = 'http://twimlets.com/message?Message%%5B0%%5D=%s'

class Game(models.Model):
    "Represents a single game of mafia."/home/markpneyer/webapps/mafia/lib/python2.6/


    name = models.CharField(max_length=32,
                            unique=True,
                            db_index =True)
    password = models.CharField(max_length=32)	

    state = models.IntegerField(default=STATE_SETUP)


    def get_ghosts(self):
	return Player.objects.filter(game=self).filter(alive=False)	
    def get_players(self):
        return Player.objects.filter(game=self).filter(alive=True)

    def get_team(self, for_team):
        return self.get_players().filter(team=for_team).filter(alive=True)

    def issue_phone_calls(self):
	"makes all the outgoing calls happen"
        players = self.get_players()
	for player in players:
	    calls = OutgoingPhoneCall.objects.filter(to_player=player)
	    for call in calls:
		call.make()
		call.delete()
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

        
	players = self.get_players() 
	for player in players:
	    player.call(TWIMLETS_BASE_URL % INTRO_TEXTS[player.team]) 
    
        self.state = STATE_PLAYING
        self.save()

        
    def check_votes(self):
        "Checks all votes to determine wether a kill should occur."
        players = self.get_players()
        
        #initialize an empty vote count for each side
        town_voters = self.get_team(TOWN)
        mafia_voters = self.get_team(MAFIA)
        
        town_votes_needed = int(1+(len(players)/2.0))

        self.check_for_kill(town_voters, town_votes_needed, TOWN)
        self.check_for_kill(mafia_voters, len(mafia_voters), MAFIA)



    def check_for_kill(self, voters, votes_needed, killing_team):
        "Determines if the given set of voters has enough votes "\
        "to kill their target."
	print "%d/%d votes needed." % (votes_needed, len(voters))
        votes = {}
        for player in self.get_players():
            votes[player] = 0

        for voter in voters:
            if voter.target and voter.target.alive:
                votes[voter.target] += 1
	max_votes = 0
	lucky_guy = None
        for victim in votes:
	    if votes[victim] > max_votes:
		max_votes = votes[victim]
		lucky_guy = victim
            if victim.alive and votes[victim] >= votes_needed:
		print "%d votes for %s. Death!" % (votes[victim],
						    victim.name)    
		self.kill(victim,killing_team)
                return
	if lucky_guy:
	    print "%s got %d votes. Not enough."  % (lucky_guy.name,
					  max_votes)
    def kill(self, victim, killing_team):
	print '%s DIED OMG WTF' % victim.name 
        victim.die()        
			          
        winner = self.check_for_victory()
        if winner:
           

	    for player in self.get_players() + self.get_ghosts():
		url = (TWIMLETS_BASE_URL % VICTORY_TEXTS[winner])
		OutgoingPhoneCall.objects.create(to_player=player,
						 twiml_url=url)
	    self.state = STATE_FINISHED	    
            self.save()
	else:
	    url = (TWIMLETS_BASE_URL % KILLED_TEXTS[victim.team])
	    OutgoingPhoneCall.objects.create(to_player=victim,
					twiml_url=url)
    def check_for_victory(self):
        town = self.get_team(TOWN).filter(alive=True)
        mafia = self.get_team(MAFIA).filter(alive=True)
        
	print "Team Sizes: %d vs %d" % (len(mafia), len(town))
        if len(mafia) >= len(town):
	    print "MAFIA WINS!"
            return MAFIA
        elif len(mafia) == 0:
	    print "TOWN WINS!"
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

    def send_message(self, message):

	msg = OutgoingMessage.objects.create(to_player=self,
					    body=message)
	return msg

    def call(self, twiml_url):
	msg = OutgoingPhoneCall.objects.create(to_player=self,
					      twiml_url = twiml_url)

	
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
class OutgoingSMS(models.Model):
    body = models.CharField(max_length=128)
    to_player  = models.ForeignKey(Player)
        
    
    #eventually we'll define a send function for this guy



class OutgoingPhoneCall(models.Model):
    twiml_url = models.CharField(max_length=512)
    to_player = models.ForeignKey(Player)

    def make(self):
	make_call(self.to_player.phone_num,
		  self.twiml_url)	
