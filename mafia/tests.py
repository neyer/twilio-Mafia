"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""
from django.conf import settings
from unittest import TestCase
from models import *
import random

class SimpleGameTest:#(TestCase):

    def setUp(self):

	print "setup"

        self.game = Game.objects.create(name="test-game")
        self.players = {}
        i = 0
        for name in ["John",
                     "Amy",
                     "Ava",
                     "Luke",
                     "Mark",
                     "Angela",
                     "Matt",
                     "Jay",
                     "Elizabeth",
                     "James"]:
            p = Player.objects.create(game=self.game,
                                      name=name,
                                      phone_num = str(i))
            self.players[name] = p
            i += 1

        self.game.start()


        self.mafia_players = self.game.get_team(MAFIA)
        self.town_players = self.game.get_team(TOWN)
        self.num_mafia = len(self.mafia_players)
        self.num_town = len(self.town_players)
        self.num_players = (self.num_mafia+self.num_town)

    def tearDown(self):
	print "teardown."
        self.game.delete()
        for player in Player.objects.all():
            player.delete()
        for vote in Vote.objects.all():
            vote.delete()


    def test_PlayerCounts(self):
        #verify that the correct number of mafia players were created

        expected_mafia = int(self.num_players*MAFIA_FRACTION)
        self.failUnlessEqual(expected_mafia,self.num_mafia)
        

    def test_MafiaKill(self):
        #verify that the mafia don't get any kills
        #until they all vote for the same player


        mafia_votes = 0
        for mafia_player in  self.mafia_players:
            v = Vote.objects.create(player=mafia_player,
                                    target=self.town_players[0])
            v.process()
	    self.game.update_tick()
            
            mafia_votes += 1

            self.failUnlessEqual(Player.objects.get(id=self.town_players[0].id).alive,
                                 mafia_votes < self.num_mafia)

            for player in self.game.get_team(TOWN)[1:]:
                self.failUnlessEqual(player.alive,True)

    def test_TownKill(self):
        #verify that half the town members can kill a mafia player
        town_votes = 0
        town_votes_needed = int((self.num_town+self.num_mafia)/2.0 + 1)

        for town_player in self.game.get_team(TOWN):
            v  = Vote.objects.create(player=town_player,
                                     target=self.mafia_players[0])
            v.process()
	    self.game.update_tick()
            town_votes+= 1

	    living_mafia = len(self.game.get_team(MAFIA))
            self.failUnlessEqual(living_mafia == self.num_mafia, 
                                 town_votes < town_votes_needed)

            for player in self.game.get_team(MAFIA)[1:]:
                self.failUnlessEqual(player.alive, True)

    def test_TownWins(self):

	for mafia_player in self.mafia_players:
	    for town_player in self.game.get_team(TOWN):
		v = Vote.objects.create(player=town_player,
					target=mafia_player)
		v.process()
		self.game.update_tick()
    
	game = Game.objects.get(id=self.game.id)
	self.failUnlessEqual(game.state, STATE_FINISHED)


    def test_MafiaWins(self):
	town = self.game.get_team(TOWN)
	for town_dude in town:
	    votes_for_this_dude = 0
	    for mafia_dude in self.game.get_team(MAFIA):
		v = Vote.objects.create(player=mafia_dude,
					target=town_dude)
		v.process()
		self.game.update_tick()
		votes_for_this_dude += 1	
		#refresh this guy from the DB
		town_dude = Player.objects.get(id=town_dude.id)
		self.failUnlessEqual(town_dude.alive,
				    votes_for_this_dude < self.num_mafia)

	game = Game.objects.get(id=self.game.id)
	self.failUnlessEqual(game.state, STATE_FINISHED)

class SmallGameTests(TestCase):
    pass
    
from django.test import Client

class TestPlayer:
    def __init__(self,name, number):
	self.id = None
	self.name = name
	self.number = number

    def get(self):
	return Player.objects.get(id=self.id)

    
class HTTPStackTest(TestCase):
    "A tester that sends sms messages to the server " \
    "and checks database to make sure things are gravy."

    def get_existing_player(self, phone_number, name):
	"gets the player if it exists, asserts if it doesn't."
	players = Player.objects.filter(phone_num=phone_number,
					name=name)
	self.failUnlessEqual(len(players),1)
	return players[0]

    def send_sms_message(self, from_num, message):
	"gets the url response from sending the message."

	client = Client()
	response = client.post('/mafia/sms', 
				    {'From': from_num,
				    'Body': message})

	self.failUnlessEqual(response.status_code,200)
	return response	

    def do_mafia_kill(self):	
	"has the mafia kill the first townsperson"
	town_players = self.game.get_team(TOWN)
	victim = town_players[0]
	mafia_players = self.game.get_team(MAFIA)
	for mafia_dude in mafia_players:
	    #before any vote, this guy shouldn't be dead
	    print "%s voting for %s." % (mafia_dude.name,
					    victim.name)	
	    self.failUnlessEqual(victim.alive,  True)
	    self.send_sms_message(mafia_dude.phone_num,
				  "vote %s" % victim.name)
	    self.game.update_tick() 
	    #update this guy from the database
	    victim = Player.objects.get(id=victim.id)
	    
	    
	self.failUnlessEqual(victim.alive, False)
	self.game.update_tick()
    
    def do_town_kill(self):
	"has the town players kill a mafia person"
	town_players = self.game.get_team(TOWN)
	mafia_players = self.game.get_team(MAFIA)
	
	town_count = len(town_players)
	mafia_count = len(mafia_players)

	if town_count < mafia_count:
	    raise Exception("Game has already ended wtf.")
	victim = mafia_players[0]
	votes = 0
	votes_needed = int(1+(town_count+mafia_count)*0.5)
	
	for town_guy in town_players:
	    self.send_sms_message(town_guy.phone_num,
	    		      "vote %s" % victim.name)
	    votes += 1
	    self.game.update_tick()
	    victim = Player.objects.get(id=victim.id)
	    self.failUnlessEqual(victim.alive,
	    		     votes < votes_needed)
    
    def assert_team_sizes(self, town, mafia):
	"asserts that the teams are the specified sizes"
	town_team = self.game.get_team(TOWN)
	mafia_team = self.game.get_team(MAFIA)
	self.failUnlessEqual(town, len(town_team))
	self.failUnlessEqual(mafia, len (mafia_team))	
    
    def setUp(self):
	#creates a game, has two players join it
	#and starts the game.
	game_name = 'game1'
	game_password = 'pass1'

	num_testers = 10
	testers = [ TestPlayer(str(x), str(100000+x))
		    for x in range(num_testers)]

	#the first guy shall be the admin
	admin = testers[0]
        	
	creation_body = 'new %s %s %s' % (admin.name,
					  game_name,
					 game_password)
	self.send_sms_message(admin.number, creation_body)
	
	#make sure a game has been created in the database
	games = Game.objects.filter(name=game_name)
	self.failUnlessEqual(len(games),1)
	players = Player.objects.filter(phone_num=admin.number)
	self.failUnlessEqual(len(players),1)
	self.failUnlessEqual(players[0].game, games[0])

	game = games[0]
	self.game = game
	admin.id = players[0].id
	self.failUnlessEqual(game.state,STATE_SETUP)

	for player in testers[1:]:
	    msg_body = "join %s %s %s" % (player.name,
					  game_name,
					  game_password)
	    self.send_sms_message(player.number,
				 msg_body)
	    players = Player.objects.filter(phone_num=player.number)	    
	    self.failUnlessEqual(len(players),1)
	    player.id = players[0].id
	    self.failUnlessEqual(players[0].game,game)
				 

	for player in testers:
	    print "%s has id %s" % (player.name, player.id)
	#once everybody is in,  start the game
	self.send_sms_message(admin.number,
			       "start")
	#make sure the game has started
	game = Game.objects.get(id=game.id)
	self.game = game
	self.failUnlessEqual(game.state,STATE_PLAYING)

	#make sure that the number of players is correct
	num_mafia = int(num_testers*MAFIA_FRACTION)
	num_town = num_testers - num_mafia
	self.assert_team_sizes(num_town, num_mafia)

    def tearDown(self):
	for vote in Vote.objects.all():
	    vote.delete()
	for player in Player.objects.all():
	    player.delete()
	self.game.delete()

    def test_SeeSaw(self):
	"first mafia kills, then town, then mafia..."
	#now have the mafia kill two townspeople
	for x in range(2):
	    self.do_mafia_kill()
	#make sure the town team has been fixed
	self.assert_team_sizes(6,2)

	#print "####################################"
	#now have the town kill two mafia people
	for x in range(1):
	    self.do_town_kill()
	
	#make sure two mafia guys are dead
	self.assert_team_sizes(6, 1)
	#at this point, 2 towns people are dead
	#and two mafia are dead
	#that means we have 5 townspeople and 1 mafia left
	for x in range(3):
	    self.do_mafia_kill()
	self.assert_team_sizes(3,1)
    
	#but the town wins in the end!
	self.do_town_kill()
	#at this point the game should be over
	#as the mafia has won.
	self.game = Game.objects.get(id=self.game.id)  
	self.failUnlessEqual(self.game.state,STATE_FINISHED)  

    def test_QuickMafiaWin(self):
	for x in range(6):	    
	    print "Checking state before killing player %d."%x
    	    self.failUnlessEqual(self.game.state,STATE_PLAYING)
	    self.do_mafia_kill();
	    self.game = Game.objects.get(id=self.game.id)
	self.failUnlessEqual(self.game.state,STATE_FINISHED)
