from flask import Flask, render_template, request
from flask_socketio import disconnect, emit, SocketIO
import monopoly_game

SERVER = Flask(__name__)
SERVER.config['SECRET KEY'] = 'svonwoudnwvob1235#'
SOCKETIO = SocketIO(SERVER)
ANNOUNCEMENT = 'ANNOUNCEMENT'
COLORS = ['#0000FF', '#FFA500', '#FF6347', '#FFF000', '#228C22', '#800080']
GAME = monopoly_game.Game()

players = [None, None, None, None, None, None]


@SERVER.route('/')
def sessions():
    # Method to handle the default initial connection by a user over HTTP
    return render_template('index.html')


@SOCKETIO.on('connect')
def connect():
    # Method to handle the socket connection from a user after the user has rendered the index.html

    # This if block is a placeholder for now, as we are only implementing one game at a time.
    # This can be used to manage multiple game sessions in the future if that is desired.
    if None not in players:
        emit('session full')
        return
    print('User connected')
    player_number_base = players.index(None)
    players[player_number_base] = request.sid
    player_name = 'Player'+str(player_number_base+1)
    player_color = COLORS[player_number_base]
    emit(
        'user connect',
        {
            'user_name': ANNOUNCEMENT,
            'message': player_name+' connected',
            'player_name': player_name,
            'player_color': player_color
        },
        broadcast=True
    )


@SOCKETIO.on('disconnect')
def handle_disconnect():
    # Method to handle disconnect events
    # Ends the current game context and refreshes the server
    if request.sid in players:
        user_number = players.index(request.sid)
        user = 'Player'+str(user_number+1)
        print(user+' disconnected')
        emit('new chat', {'user_name': ANNOUNCEMENT,
                          'message': user+' disconnected. Please refresh to start a new game.'}, broadcast=True)
        players[user_number] = None
        for i in range(len(players)):
            if players[i] is not None:
                user_id = players[i]
                players[i] = None
                disconnect(sid=user_id)
        GAME.reset()
    print('disconnect confirmed')


@SOCKETIO.on('new chat')
def handle_chat(json):
    # Method used to send events to and from each player in the chat. Also a framework for the rest of the user actions
    print('received event: ' + str(json))
    emit('new chat', json, broadcast=True)


@SOCKETIO.on('start game')
def start():
    playing_players = []
    for player in players:
        if player is not None:
            playing_players.append(player)
    GAME.start_game(playing_players)
    user_names = []
    for i in range(len(playing_players)):
        user_names.append('Player'+str(i+1))
    emit('start game', {'players': user_names, 'colors': COLORS}, broadcast=True)


@SOCKETIO.on('roll dice')
def roll():
    if players.index(request.sid) != GAME.current_player:
        return
    is_movement = GAME.turn_stage == 'move'
    roll_int, die_file_1, die_file_2, space, in_jail, purchased_space, messages = GAME.roll_dice()
    emit('roll result', {'die_file_1': die_file_1, 'die_file_2': die_file_2, 'roll_int': roll_int}, broadcast=True)
    if is_movement:
        move_piece(request.sid, space, in_jail)
    if purchased_space:
        purchase(request.sid, space)
    for message in messages:
        if message[-1] == '~':
            emit('new chat', {'user_name': '', 'message': message[:-1]}, broadcast=True)
        else:
            handle_chat({'user_name': ANNOUNCEMENT, 'message': message})
    update_money()


def move_piece(user_id, space, in_jail):
    player = 'Player'+str(players.index(user_id)+1)
    color = COLORS[players.index(user_id)]
    emit('move piece', {'player': player, 'space': space, 'color': color, 'in_jail': in_jail}, broadcast=True)


def update_money():
    user_names = []
    money = []
    for player in GAME.PLAYERS:
        user_names.append(player.name)
        money.append(player.money)
    emit('update money', {'players': user_names, 'money': money}, broadcast=True)


@SOCKETIO.on('chance')
def chance():
    if players.index(request.sid) != GAME.current_player or GAME.turn_stage != 'chance':
        return
    chance_card, player_position, in_jail, purchased_space, messages = GAME.chance()
    emit('chance result', {'card_content': chance_card[0]}, broadcast=True)
    if chance_card[1] in ['go to space', 'go to jail', 'movement']:
        move_piece(request.sid, player_position, in_jail)
    if purchased_space:
        purchase(request.sid, player_position)
    for message in messages:
        if message[-1] == '~':
            emit('new chat', {'user_name': '', 'message': message[:-1]}, broadcast=True)
        else:
            handle_chat({'user_name': ANNOUNCEMENT, 'message': message})
    update_money()


@SOCKETIO.on('community chest')
def community_chest():
    if players.index(request.sid) != GAME.current_player or GAME.turn_stage != 'community chest':
        return
    comchest_card, player_position, in_jail, purchased_space, messages = GAME.community_chest()
    emit('community chest result', {'card_content': comchest_card[0]}, broadcast=True)
    if comchest_card[1] in ['go to space', 'go to jail']:
        move_piece(request.sid, player_position, in_jail)
    if purchased_space:
        purchase(request.sid, player_position)
    for message in messages:
        if message[-1] == '~':
            emit('new chat', {'user_name': '', 'message': message[:-1]}, broadcast=True)
        else:
            handle_chat({'user_name': ANNOUNCEMENT, 'message': message})
    update_money()


def purchase(user_id, space):
    player_index = players.index(user_id)
    color = COLORS[player_index]
    emit('purchase', {'space': space, 'color': color}, broadcast=True)


@SOCKETIO.on('pay')
def pay(data):
    some_result = GAME.pay(data.amount, data.payer, data.recipient)
    """ TODO emit the result to the users """
    return some_result


if __name__ == '__main__':
    SOCKETIO.run(SERVER, host="0.0.0.0", port=8080, debug=True)
