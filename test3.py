



import arcade
import random
import math
import os

#from arcade.experimental.camera import Camera2D

from arcade import Point, Vector
from arcade.utils import _Vec2

import time

import pyglet



from typing import cast
import pprint

import pyglet.input.base

SCREEN_WIDTH = 700
SCREEN_HEIGHT = 700
SCREEN_TITLE = "test joystick"

def dump_obj(obj):
    for key in sorted(vars(obj)):
        val = getattr(obj, key)
        print("{:30} = {} ({})".format(key, val, type(val).__name__))


def dump_joystick(joy):
    print("========== {}".format(joy))
    print("x       {}".format(joy.x))
    print("y       {}".format(joy.y))
    print("z       {}".format(joy.z))
    print("rx      {}".format(joy.rx))
    print("ry      {}".format(joy.ry))
    print("rz      {}".format(joy.rz))
    print("hat_x   {}".format(joy.hat_x))
    print("hat_y   {}".format(joy.hat_y))
    print("buttons {}".format(joy.buttons))
    print("========== Extra joy")
    dump_obj(joy)
    print("========== Extra joy.device")
    dump_obj(joy.device)
    print("========== pprint joy")
    pprint.pprint(joy)
    print("========== pprint joy.device")
    pprint.pprint(joy.device)


def dump_joystick_state(ticks, joy):
    # print("{:5.2f} {:5.2f} {:>20} {:5}_".format(1.234567, -8.2757272903, "hello", str(True)))
    fmt_str = "{:6d} "
    num_fmts = ["{:5.2f}"] * 6
    fmt_str += " ".join(num_fmts)
    fmt_str += " {:2d} {:2d} {}"
    buttons = " ".join(["{:5}".format(str(b)) for b in joy.buttons])
    print(fmt_str.format(ticks,
                         joy.x,
                         joy.y,
                         joy.z,
                         joy.rx,
                         joy.ry,
                         joy.rz,
                         joy.hat_x,
                         joy.hat_y,
                         buttons))


def get_joy_position(x, y):
    """Given position of joystick axes, return (x, y, angle_in_degrees).
    If movement is not outside of deadzone, return (None, None, None)"""
    if x > JOY_DEADZONE or x < -JOY_DEADZONE or y > JOY_DEADZONE or y < -JOY_DEADZONE:
        y = -y
        rad = math.atan2(y, x)
        angle = math.degrees(rad)
        return x, y, angle
    return None, None, None




class MyGame(arcade.View):
    def __init__(self):
        super().__init__()

    def on_joybutton_press(self, _joystick, button):
        """ Handle button-down event for the joystick """
        print("Button {} down".format(button))
        if button == JUMPBTN:

            iced_ground_contact_list = arcade.check_for_collision_with_list(self.player_list[0], self.lowfric_list)

            if  iced_ground_contact_list == []:


                if self.physics_engine.is_on_ground(self.player_sprite) and not self.player_sprite.is_on_ladder:


                    # She is! Go ahead and jump
                    impulse = (0, PLAYER_JUMP_IMPULSE)
                    self.physics_engine.apply_impulse(self.player_sprite, impulse)



    def on_show(self):
        arcade.set_background_color(arcade.color.DARK_MIDNIGHT_BLUE)
        joys = self.window.joys
        for joy in joys:
            dump_joystick(joy)
        if joys:
            self.joy = joys[0]
            print("Using joystick controls: {}".format(self.joy.device))
            arcade.window_commands.schedule(self.debug_joy_state, 0.1)
        if not self.joy:
            print("No joystick present, using keyboard controls")
        arcade.window_commands.schedule(self.spawn_enemy, ENEMY_SPAWN_INTERVAL)

    def debug_joy_state(self, _delta_time):
        dump_joystick_state(self.tick, self.joy)


    def on_update(self, delta_time):
        self.tick += 1
        if self.game_over:
            return

        self.bullet_cooldown += 1

        for enemy in self.enemy_list:
            cast(Enemy, enemy).follow_sprite(self.player)

        if self.joy:
            # Joystick input - movement
            move_x, move_y, move_angle = get_joy_position(self.joy.move_stick_x, self.joy.move_stick_y)
            if move_angle:
                self.player.change_x = move_x * MOVEMENT_SPEED
                self.player.change_y = move_y * MOVEMENT_SPEED
                self.player.angle = move_angle + ROTATE_OFFSET
            else:
                self.player.change_x = 0
                self.player.change_y = 0

            # Joystick input - shooting
            shoot_x, shoot_y, shoot_angle = get_joy_position(self.joy.shoot_stick_x, self.joy.shoot_stick_y)
            if shoot_angle:
                self.spawn_bullet(shoot_angle)
        else:
            # Keyboard input - shooting
            if self.player.shoot_right_pressed and self.player.shoot_up_pressed:
                self.spawn_bullet(0+45)
            elif self.player.shoot_up_pressed and self.player.shoot_left_pressed:
                self.spawn_bullet(90+45)
            elif self.player.shoot_left_pressed and self.player.shoot_down_pressed:
                self.spawn_bullet(180+45)
            elif self.player.shoot_down_pressed and self.player.shoot_right_pressed:
                self.spawn_bullet(270+45)
            elif self.player.shoot_right_pressed:
                self.spawn_bullet(0)
            elif self.player.shoot_up_pressed:
                self.spawn_bullet(90)
            elif self.player.shoot_left_pressed:
                self.spawn_bullet(180)
            elif self.player.shoot_down_pressed:
                self.spawn_bullet(270)





class JoyConfigView(arcade.View):
    """A View that allows a user to interactively configure their joystick"""
    REGISTRATION_PAUSE = 1.5
    NO_JOYSTICK_PAUSE = 2.0
    JOY_ATTRS = ("x", "y", "z", "rx", "ry", "rz")

    def __init__(self, joy_method_names, joysticks, next_view, width, height):
        super().__init__()
        self.next_view = next_view
        self.width = width
        self.height = height
        self.msg = ""
        self.script = self.joy_config_script()
        self.joys = joysticks
        arcade.set_background_color(arcade.color.WHITE)
        if len(joysticks) > 0:
            self.joy = joysticks[0]
            self.joy_method_names = joy_method_names
            self.axis_ranges = {}

    def config_axis(self, joy_axis_label, method_name):
        self.msg = joy_axis_label
        self.axis_ranges = {a: 0.0 for a in self.JOY_ATTRS}
        while max([v for k, v in self.axis_ranges.items()]) < 0.85:
            for attr, farthest_val in self.axis_ranges.items():
                cur_val = getattr(self.joy, attr)
                if abs(cur_val) > abs(farthest_val):
                    self.axis_ranges[attr] = abs(cur_val)
            yield

        max_val = 0.0
        max_attr = None
        for attr, farthest_val in self.axis_ranges.items():
            if farthest_val > max_val:
                max_attr = attr
                max_val = farthest_val
        self.msg = f"Registered!"

        setattr(pyglet.input.base.Joystick, method_name, property(lambda that: getattr(that, max_attr), None))

        # pause briefly after registering an axis
        yield from self._pause(self.REGISTRATION_PAUSE)

    def joy_config_script(self):
        if len(self.joys) == 0:
            self.msg = "No joysticks found!  Use keyboard controls."
            yield from self._pause(self.NO_JOYSTICK_PAUSE)
            return

        for joy_axis_label, method_name in self.joy_method_names:
            yield from self.config_axis(joy_axis_label, method_name)

    def on_update(self, delta_time):
        try:
            next(self.script)
        except StopIteration:
            self.window.show_view(self.next_view)

    def on_draw(self):
        arcade.start_render()
        arcade.draw_text("Configure your joystick", self.width/2, self.height/2+100,
                         arcade.color.BLACK, font_size=32, anchor_x="center")
        arcade.draw_text(self.msg, self.width/2, self.height/2,
                         arcade.color.BLACK, font_size=24, anchor_x="center")

    def _pause(self, delay):
        """Block a generator from advancing for the given delay. Call with 'yield from self._pause(1.0)"""
        start = time.time()
        end = start + delay
        while time.time() < end:
            yield

            
class InstructionView(arcade.View):

    def __init__(self):
        
        super().__init__()
        
        pass





    
    
    def on_show(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        arcade.set_viewport(0, SCREEN_WIDTH - 1, 0, SCREEN_HEIGHT - 1)

    def on_draw(self):
        """ Draw this view """
        arcade.start_render()
        arcade.draw_text("Instructions Screen", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                         arcade.color.WHITE, font_size=50, anchor_x="center")
        arcade.draw_text("Click to advance", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2-75,
                         arcade.color.WHITE, font_size=20, anchor_x="center")



        
    def on_mouse_press(self, _x, _y, _button, _modifiers):
        """ If the user presses the mouse button, start the game. """
        game_view = GameView()
        game_view.setup(level=1)
        arcade.set_background_color(arcade.csscolor.BLACK)


        try:            
            pass
        except ValueError:
            print("music already finished")  # ValueError: list.remove(x): x not in list   media.Source._players.remove(player)

        self.window.show_view(game_view)


    def on_update(self, delta_time):
        """ Movement and game logic """
        #pressed = self.window.joys[0].on_joybutton_press    
        #print(pressed)   # <bound method Joystick.on_joybutton_press of <pyglet.input.base.Joystick object at 0x7f5169264d90>>

        #print(type(pressed))  #  <class 'method'>

        joy_dico = self.window.joys[0]



        btns = joy_dico.buttons
        print(btns)
        #print(type(btns))        # list

        print(">>>>")


        print(joy_dico.button_controls)   # [Button(raw_name=BTN_A), Button(raw_name=BTN_B), Button(raw_name=BTN_X), Button(raw_name=BTN_Y), Button(raw_name=BTN_TL), Button(raw_name=BTN_TR), Button(raw_name=BTN_SELECT), Button(raw_name=BTN_START), Button(raw_name=BTN_MODE), Button(raw_name=BTN_THUMBL), Button(raw_name=BTN_THUMBR)]

        print(joy_dico.button_controls[0].__dict__)

        print("_______*******")
        #print(joy_dico.button_controls.BTN_A)

        joy_dico = self.window.joys[0]

        BTN_A = joy_dico.button_controls[0]
        BTN_B = joy_dico.button_controls[1]
        BTN_X = joy_dico.button_controls[2]
        BTN_Y = joy_dico.button_controls[3]
        BTN_TL = joy_dico.button_controls[4]
        BTN_TR = joy_dico.button_controls[5]
        BTN_SELECT = joy_dico.button_controls[6]
        BTN_START = joy_dico.button_controls[7]
        BTN_MODE = joy_dico.button_controls[8]
        BTN_THUMBL = joy_dico.button_controls[9]
        BTN_THUMBR = joy_dico.button_controls[10]


        print(f"\n     BTN_A     ---->       {BTN_A}")


        BTN_list = [BTN_A,BTN_B,BTN_X,BTN_Y, BTN_TL, BTN_TR, BTN_SELECT, BTN_START, BTN_MODE, BTN_THUMBL, BTN_THUMBR]

        for BTN in BTN_list:
            if BTN._value == 1:
                print(f"=====>   >=====>     ====>    {BTN.raw_name}")


    def joy_reaction_A(self):

        #joy_dico = self.window.joys[0]

        #print(f"=====>   >=====>     ====>    {joy_dico.buttons}")

        pass





class GameView(arcade.View):

    def __init__(self):
        
        super().__init__()
        
        pass


    def setup(self, level):

        pass
        


    
    
    def on_show(self):
        """ This is run once when we switch to this view """
        arcade.set_background_color(arcade.csscolor.DARK_SLATE_BLUE)

        arcade.set_viewport(0, SCREEN_WIDTH - 1, 0, SCREEN_HEIGHT - 1)

    def on_draw(self):
        """ Draw this view """
        arcade.start_render()
        arcade.draw_text("GameView Screen", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                         arcade.color.GREEN, font_size=50, anchor_x="center")
        arcade.draw_text("Click to advance", SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2-75,
                         arcade.color.RED, font_size=20, anchor_x="center")




    def on_update(self, delta_time):

        #if self.joy
        if self.window.joys:
            joy = self.window.joys[0]

            print(joy.__dict__)
            print(joy.buttons)
            # Joystick input - movement
            #move_x, move_y, move_angle = get_joy_position(self.joy.move_stick_x, self.joy.move_stick_y)
            move_x, move_y, move_angle = get_joy_position(joy.move_stick_x, joy.move_stick_y)
            #move_x, move_y, move_angle = get_joy_position(self.window.joys.move_stick_x, self.window.joys.move_stick_y)

            if move_angle:
                self.player.change_x = move_x * MOVEMENT_SPEED
                self.player.change_y = move_y * MOVEMENT_SPEED
                self.player.angle = move_angle + ROTATE_OFFSET
            else:
                self.player.change_x = 0
                self.player.change_y = 0

            # Joystick input - shooting
            shoot_x, shoot_y, shoot_angle = get_joy_position(self.joy.shoot_stick_x, self.joy.shoot_stick_y)
            if shoot_angle:
                self.spawn_bullet(shoot_angle)










def main():

    #window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, fullscreen=False)

    

    #start_view = GameView()
    #window.show_view(start_view)
    
    #start_view.setup()
    #start_view.setup(level=1)

    start_view = InstructionView()
    #start_view = GameView()

    window.show_view(start_view)









    window.joys = arcade.get_joysticks()
    for j in window.joys:
        j.open()
    #joy_config_method_names = (
    #    ("Move the movement stick left or right", "move_stick_x"),
    #    ("Move the movement stick up or down", "move_stick_y"),
    #    ("Move the shooting stick left or right", "shoot_stick_x"),
    #    ("Move the shooting stick up or down", "shoot_stick_y"),
    #)
    game = InstructionView()

    print(dir(window.joys[0]))

    print("---")

    print(window.joys[0].__dict__)

    print("iii---")

    print("\n\n\n\n\n")






    #window.show_view(JoyConfigView(joy_config_method_names, window.joys, game, SCREEN_WIDTH, SCREEN_HEIGHT))

    
    arcade.run()


if __name__ == "__main__":
    main()