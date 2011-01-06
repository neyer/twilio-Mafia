# Create your views here

from models import *
from django.http import HttpResponse
from django.template  import Context, loader
from django.contrib.csrf.middleware import csrf_exempt

TWIML_BASE  =	"<Response>" \
		"  <Sms>" \
		"%s" \
		" </Sms>"\
		"</Response>"

class SMSCommand:
    "Dectorator for making sure people send the right number of args "\
    "to our functions. "\
    "Give it the name of the function, and then a tuple for each arg. "\
    "The tuple should contain the type of argument and its name. "\
    "has_args will check the function call and handle errors with "\
    "a response message back to the player." \
    "Each SMSCommand should take two arguments: a player, and the command "\
    

    def __init__(self,name,public=True,*arg_descriptors):
	self.name = name	
	self.arg_descs = arg_descriptors
	self.public = public 

    def __call__(self, func):
	def real_func(*args, **kw_args):
	    if len(args) == 0:
		return "An error has occured..." 

	    from_num = args[0]
	    body = args[1]
	    body_parts = body.split()
	    real_args = []
	    #if the command is public, we can just pass the # through
	    #to the calling function
	    #if the command is private, we check to see if there's
	    #a valid users first
	    if not self.public:	
		players = Player.objects.filter(phone_num=from_num)
		if not players:
		    return "You must join a game to do that."
		from_num = players[0]
	    #make sure we have the right number of args
	    #the first arg is the function name so we don't count it
	    num_args = len(body_parts) - 1
	    req_args = len(self.arg_descs)
	    if num_args < req_args:
		res =  "Wrong number of args. "
		res +=  "You sent %d, we want %d. " % (num_args,
						    req_args)
		res += "Syntax: %s " % self.name
		res += ' '.join(desc[1] for desc in self.arg_descs)
		return res

	    #make sure each argument is of the correct type
	
	    real_args = [body_parts[i+1] for i in range(req_args)]
	    return  func(*([from_num] + [body] + real_args))
	real_func.__doc__ = func.__doc__ 
	return real_func


#######################
# Base SMS handler
#######################
@csrf_exempt
def sms(request):
    global commands

    if not ('From' in request.REQUEST and 'Body' in request.REQUEST):
	return HttpResponse('go away plz')
    sender_num = request.REQUEST['From']
    msg = request.REQUEST['Body']
    msg = msg.lower()


    parts = msg.split()
    if not parts[0] in commands:
	res = TWIML_BASE % "That is not a valid command. "\
	      "Send 'help' to see valid commands"
    else:
	out_msg = commands[parts[0]](sender_num, msg)
	if out_msg:
	    res = TWIML_BASE % out_msg
	else:
	    res = '<Response></Response>'
    return HttpResponse(res)





######################
#  Individual Commands
######################


######################
# Create a new game 
######################
@SMSCommand("new", True,
	    (str, 'player_name'),
	    (str,"game_name"),
	    (str,"password")
	    )
def handle_new(player_num, cmd, player_name,game_name, password):
    "new <player_name> <game_name> <password>: "\
    "creates a new game with the given name."	
    games = Game.objects.filter(name=game_name)
    if games:
	game = games[0]
	if game.state == STATE_FINISHED:
	    game.delete()
	else:
	    return "Sorry, %s. A game by that name exists." % player_name 
   
    players = Player.objects.filter(phone_num=player_num)
    if players:
	if player.game.state == STATE_FINISHED:
	    player.delete()
	else:
	    return "Sorry, %s. You are already in a game." % player_name

    game = Game.objects.create(name=game_name,
				password=password)
    Player.objects.create(phone_num=player_num,
			 name=player_name,
			 game=game,
			is_admin=True)
    return "Hello, %s @ %s. New game %s created with password %s." % (player_name, 
    player_num,
						    game_name,
						    password)




######################
# Join a game 
######################
@SMSCommand("join",True,
	    (str,'your_name'),
	    (str,'game_name'),
	    (str,'password'))
def handle_join(player_num, cmd, player_name, game_name, password):
    "join <player_name> <game_name> <password>: " \
    "Join game <game_name> with password <password> " \
    "as player <player_name>."	
    #first, see if this player is alreay playing a game
    players = Player.objects.filter(phone_num=player_num)
    if players:
	if not players[0].alive:
	    players[0].delete();
	else:
	    return "Sorry, %s. You are already in a game." % player_name
    games = Game.objects.filter(name=game_name)
    if not games:
	return "Sorry, %s. No game by that name exists." % player_name

    game = games[0]
    if not game.password == password:
	return "Sorry, %s. That was not the correct password."
    if not game.state == STATE_SETUP:
	return "Sorry, %s. That game must has already started."
    players =  Player.objects.filter(game=game,name=player_name)
    if players:
	return "Sorry, %s. A player by that name already exists." % player_name 
    Player.objects.create(phone_num=player_num,
			    name=player_name,
			    game=game,
			    is_admin=True)
    return "You have joined the game. Good luck!"


######################
# Start a game 
######################
@SMSCommand('start',False)
def handle_start(player, cmd):
    "<start>: start the game, or restart a finished game."
    #make sure the game hasn't started already
    if player.game.state == STATE_PLAYING:
	return "Sorry, %s. The game has already started!" % player.name
    
    if not player.is_admin:
	return "Sorry, %s. You did not create this game." % player.name

    player.game.start()
    return "Game started!"



######################
# Vote for a player
######################
@SMSCommand("vote",False,
	    (str,'player_name'))
def handle_vote(player, cmd,  other_player):
    "vote <player>: vote to kill <player>."
    #make sure this player's game has started.
    if player.game.state != STATE_PLAYING:
	return "You cannot vote until the game has begun!"
    #see if this other player exists
    same_game =  Player.objects.filter(game=player.game)
    other_guys = same_game.filter(name=other_player)
    if not other_guys:
	return "Sorry,  %s. No player %s exists in game %s." % (player.name, other_player, player.game.name)

    if not player.alive:
	return "Silly %s, ghosts can't vote." % (player.name)
    other_guy = other_guys[0]
    Vote.objects.create(player=player,
			target=other_guy).process()
    return "Your vote has been recorded."

#####################
#list all  players
#######################
@SMSCommand("who",False)
def handle_who(player, cmd):
    "who: Find out who is in the game."
    players = player.game.get_players()
    message = ', '.join([p.name for p in players])
    
    if player.team == MAFIA or (not player.alive):
	message += '. Mafia players are: '+ ', '.join([p.name 
						for p 
						in players
						if p.team == MAFIA])
    
    return message
    

######################################
# say a message to other players
######################################
@SMSCommand("say",False)
def handle_say(player,cmd):
    "say: Send a message to all the other players."
    #get a list of all the players in this game	
    message = player.name+': '+' '.join(cmd.split(' ')[1:])
    players = player.game.get_players()

    for player in players:
	player.send_message(message)
	 
    return None


######################################
# say a message to the mafia players
######################################
@SMSCommand("mafia",False)
def handle_mafia(player,cmd):
    "mafia: Send a message to the mafia."
    #sends the message to mafia players and dead players
    message = player.name+': '+' '.join(cmd.split(' ')[1:])
    players = player.game.get_players().filter(team=MAFIA)

    for player in players:
	player.send_message(message)

    players = player.game.get_players(False).filter(alive=False)
    
    for player in players:
	player.send_message(message)

    town_players = player.game.get_TEAM(TOWN)

    for player in town_players:
	player.send_message("The mafia are talking.")
    return None


######################################
# find out who people are voting for
#######################################
@SMSCommand("votes",False)
def handle_votes(player, cmd):
    "votes: Find out how many players are voting for each player."
    #get a list of all players and how many votes they have
    votes = player.game.get_votes(player.teaim)

    msg = ', '.join(['%s: %d' % (key.name, votes[key])
		      for key
			in votes])
    return msg


########################################
# gets help for a command
########################################
@SMSCommand("help",True)
def handle_help(player, cmd):
    "help: lists all commands. "\
    "help <name>: gives help for command <name>."
    global commands
    #figure out if they just want the list of commands
    #or help w/ a specific command
    words = cmd.split()
    if len(words) == 1:
	return "Commands are: "+', '.join([key for key in commands])
    elif not words[1] in commands:
	return "There is no such command."
    else:
	return commands[words[1]].__doc__ 


##########################################
# ends the game. only admins can do it.
##########################################
@SMSCommand("end",False)
def handle_end(player, cmd):
    "end: ends the game. "
    if not player.is_admin:
	return "You do not have permission to end this game. "

    #kick all the players out of the game
    for player in player.game.get_players(False):
	player.delete()
    game.delete()

    return "Game deleted."


commands = {'new' : handle_new,
	    'join' : handle_join,
	    'start': handle_start,
	    'vote':  handle_vote,
	    'say' : handle_say,
	    'who' : handle_who,
	    'mafia' : handle_mafia,
	    'votes' : handle_votes,
	    'help' : handle_help,
	    'end' : handle_end
	    }

