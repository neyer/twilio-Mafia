from django.db import models
import random
from twilio_wrapper import *
# Create your models here.
from urllib import urlencode


#game states
STATE_SETUP = 1
STATE_PLAYING = STATE_SETUP+1
STATE_FINISHED = STATE_PLAYING+1

MAFIA_FRACTION = 0.2

#teams
TOWN = 1
MAFIA = 2

GAME_NUMBER = '5136731535'

INTRO_TEXTS = { TOWN : 'Hello. You are a part of the town. '\
			'You have heard rumors of mafia activity. '\
			'Your goal is to  identify the members of the mafia '\
			'and bring them to justice. You can text '\
			'vote name to cast your vote for the town to kill '\
			'name next. Iyou need help, text help. Good luck!',

		MAFIA: 'Hello. You are a part of the mafia. '\
			'Your goal is to kill the town members one by one '\
			'until half the town is a mafia member. ' \
			'You can text vote name to cast your vote '\
			'for name to be the next hit. If you need help '\
			'text help.'
	    }

KILLED_TEXTS = { TOWN : 'You have been accused by the town of mafiary '\
			'and are sentenced to die. Have a nice day.',
		 MAFIA: 'You have been killed by the mafia. Have a nice day.'
	    }
OBITUARY_TEXTS = {  TOWN : 'The town accused and hanged %s .',
		    MAFIA : '%s died violently in the night.'
		}

VICTORY_TEXTS = { MAFIA : 'The mafia have taken over the town. ' \
			  'May god have mercy on us all.',
		  TOWN : 'The town has killed off the mafia! ' \
			 'Now we can sleep safe at night.'
		  }
TWIMLETS_BASE_URL = 'http://twimlets.com/message?Message%%5B0%%5D=%s'

def make_url_for_text(text):
    return TWIMLETS_BASE_URL % (text.replace(' ','%20'))


######################################
# Game: each game has its own model
# a player can only be in one game
######################################
class Game(models.Model):
    "Represents a single game of mafia."


    name = models.CharField(max_length=32,
                            unique=True,
                            db_index =True)
    password = models.CharField(max_length=32)	

    state = models.IntegerField(default=STATE_SETUP)


    ###########################################
    # Utility functions for getting sets of players
    ######################################


    def get_ghosts(self):
	return Player.objects.filter(game=self).filter(alive=False)	

    def get_players(self, alive_only=True):
        players =  Player.objects.filter(game=self)
	if alive_only: players = players.filter(alive=True)
	return players

    def get_team(self, for_team):
        return self.get_players().filter(team=for_team).filter(alive=True)


    ####################################
    # Utility communication functions
    ####################################


    def call_everyone(self, twiml_url, alive_only=True):
	for player in self.get_players(alive_only):
	    player.call(twiml_url)

    def message_everyone(self, message, alive_only=True):
	for player in self.get_players(alive_only):
	    player.send_message(message)
	
    ###############################################
    # Starting or restarting the game
    ###############################################
    def start(self):
	"starts the game, telling each player his role."
	#don't filter out the dead players
	#since we're starting the game again
	players = self.get_players(False)
        num_players = len(players)
        num_mafia = num_players*MAFIA_FRACTION
						
        unassigned = [player for player in players]
        random.shuffle(unassigned)

        i = 0
        for player in unassigned:
	    #the player is a live now
	    player.alive = True
            if i >= num_mafia:
                player.assign_team(TOWN)
		player.send_message('The game has started! You are a townsperson. '\
		'Text "help" for help.')
            else:
                player.assign_team(MAFIA)
		player.send_message('The game has started! You are in the mafia. '\
		'Text "help" for help.')
            i += 1

        
	players = self.get_players() 
	
    
        self.state = STATE_PLAYING
        self.save()


    ##############################
    #   Voting Methods
    #  Root method is check_votes 
    # this is basically a wrapper around check_for_kill
    ##############################
        
    def check_votes(self):
	if not self.state == STATE_PLAYING:
	    return
        "Checks all votes to determine wether a kill should occur."
        players = self.get_players()
        
        town_votes_needed = int(1+(len(players)/2.0))

        self.check_for_kill(TOWN, town_votes_needed)
        self.check_for_kill(MAFIA, len(self.get_team(MAFIA)))

    def get_votes (self, voting_team):
        "Returns a mapping: player -> # of votes"
	#get the list of players that are voting
	if voting_team == MAFIA:
	    voters = self.get_team(MAFIA)
	else:
	    voters = self.get_team(TOWN)

	#now figure out how many votes each player gets
	votes = {}
	for player in self.get_players():
            votes[player] = 0

        for voter in voters:
            if voter.target and voter.target.alive:
                votes[voter.target] += 1
	return votes

    def check_for_kill(self, voting_team, votes_needed):
        "Determines if the given set of voters has enough votes "\
        "to kill their target."
        votes = self.get_votes(voting_team)
	max_votes = 0
	lucky_guy = None
        for victim in votes:
	    if votes[victim] > max_votes:
		max_votes = votes[victim]
		lucky_guy = victim
            if victim.alive and votes[victim] >= votes_needed:
		print "%d votes for %s. Death!" % (votes[victim],
						    victim.name)    
		self.kill(victim,voting_team)
                return
	if lucky_guy:
	    print "%s got %d votes. Not enough."  % (lucky_guy.name,
					  max_votes)
    #####################################
    # Killing and checking for victory
    #####################################
    def kill(self, victim, killing_team):
	print '%s DIED OMG WTF' % victim.name 
        victim.die(killing_team)        
			          
        winner = self.check_for_victory()

        if winner:
	    twiml_url = make_url_for_text(VICTORY_TEXTS[winner]) 
	    self.call_everyone(twiml_url,False)
	    self.message_everyone(VICTORY_TEXTS[winner])
	    self.state = STATE_FINISHED	    
            self.save()
	else:
	    url = make_url_for_text(KILLED_TEXTS[killing_team])
	    victim.call(url)
	    everyone_message_text = OBITUARY_TEXTS[killing_team] % victim.name
	    self.message_everyone(everyone_message_text,False)


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

    ################################################
    #Updating the game as a result of a turn changing
    ################################################

    def update_tick(self):
	self.check_votes()

    ###############################################
    # Getting statistics for games
    ###############################################

    def get_total_votes(self):
	vote_counts = {}
	for player in self.get_players(False):
	    votes = Vote.objects.filter(player=player)
	    vote_counts[player.name] = len(votes)

	return vote_counts


    def get_target_counts(self):
	target_counts = {}
	for target in self.get_players(False):
	    votes = Vote.obejcts.filter(target=target)
	    target_counts[target.name] = len(votes)

	return target_counts
	
    

    

	

	
	 

#######################################
#  Player: each caller in the game has a player
# players are assigned one of two teams, and are alive or dead.
# the admin player is the only one who can start the game.
#######################################
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

    def die(self, killing_team):
	self.alive = False
	self.save()
	


    def send_message(self, message):

	msg = OutgoingSMS.objects.create(to_player=self,
					    body=message)
	msg.send()
	return msg

    def call(self, twiml_url):
	call = OutgoingPhoneCall.objects.create(to_player=self,
					      twiml_url = twiml_url)
	call.make()

#######################################################
#  Actions
# actions are recorded so we can keep track of how many
# votes each player recieved etc.
#######################################################	
#an abstract base class for all player performed actions
class Action(models.Model):
    player = models.ForeignKey(Player)
    timestamp = models.DateTimeField(auto_now_add=True)

#####################################
#the player votes for another 
###############################
class Vote(Action):
    target = models.ForeignKey(Player)

    def process(self):
        "Causes the action to play itself out"
        self.player.target = self.target
        self.player.save()



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
    def send(self):
	send_sms(self.to_player.phone_num,
		    self.body)




class OutgoingPhoneCall(models.Model):
    twiml_url = models.CharField(max_length=512)
    to_player = models.ForeignKey(Player)

    def make(self):
	make_call(self.to_player.phone_num,
				  self.twiml_url)	
