"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from unittest import TestCase
from models import *
import random

class SimpleGameTest(TestCase):

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
		votes_for_this_dude += 1	
		#refresh this guy from the DB
		town_dude = Player.objects.get(id=town_dude.id)
		self.failUnlessEqual(town_dude.alive,
				    votes_for_this_dude < self.num_mafia)

	game = Game.objects.get(id=self.game.id)
	self.failUnlessEqual(game.state, STATE_FINISHED)


from django.test import Client

class BrowserTest(TestCase):

    def get_existing_player(self, phone_number, name):
	"gets the player if it exists, asserts if it doesn't."
	players = Player.objects.filter(phone_num=phone_number,
					name=name)
	self.failUnlessEqual(len(players),1)
	return players[0]
	
    def test_JoinAndStart(self):
	#creates a game, has two players join it
	#and starts the game.
	game_name = 'game1'
	game_password = 'pass1'
	
	players = [ { 'name' : 'frank',
		    'phone' : '123'},
		    {'name' : 'jim',
		      'phone' : '456'},
		    {'name' : 'fred',
		      'phone' : '789'} ]

	frank = players[0]
	jim = players[1]
	fred = players[2]

	frank['client'] = Client()
	creation_body = 'new %s %s %s' % (frank['name'], game_name,
						    game_password)
	response = frank['client'].post('/mafia/sms', 
				    {'From': frank['phone'],
				    'Body': creation_body})
	
	#make sure we get a status ok
	self.failUnlessEqual(response.status_code,200)
	
	#make sure a game has been created in the database
	games = Game.objects.filter(name=game_name)
	self.failUnlessEqual(len(games),1)
	players = Player.objects.filter(phone_num=frank['phone'])
	self.failUnlessEqual(len(players),1)
	self.failUnlessEqual(players[0].game, games[0])

	game = games[0]
	frank['player'] = players[0]
	self.failUnlessEqual(game.state,STATE_SETUP)


	#have jim and fred join the game
	jim['client'] = Client()
	jim_body = "join %s %s %s" % (jim['name'],
					game_name, 
					game_password) 
	jim['response'] = jim['client'].post('/mafia/sms',
					{'From' :jim['phone'],
	
    				 'Body' : jim_body})
	self.failUnlessEqual(jim['response'].status_code,200)

	#make sure we have the player jim
	jim['player'] = self.get_existing_player(jim['phone'],
						 jim['name'])	
	self.failUnlessEqual(jim['player'].game,game)
	#fred's turn
	fred['client'] = Client()
	fred_body = "join %s %s %s" % (fred['name'],
					game_name, 
					game_password) 
	fred['response'] = fred['client'].post('/mafia/sms',
					{'From' :fred['phone'],
					'Body' : fred_body})
	self.failUnlessEqual(fred['response'].status_code,200)

	#make sure we have the player fred
	fred['player'] = self.get_existing_player(fred['phone'],
						 fred['name'])		
	self.failUnlessEqual(fred['player'].game,game)
