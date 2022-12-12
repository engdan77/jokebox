from machine import Pin, I2C
import ssd1306
import time
import random
import uasyncio
import network
import web

__author__ = "daniel@engvalls.eu"

MCU_TYPE = "ESP8266"
WOKWI = False

if MCU_TYPE == "ESP8266":
    pins = {"sda": 5, "scl": 4, "button": 4, "led": 14}
else:
    pins = {"sda": 21, "scl": 22, "button": 23, "led": 12}


SSID = "TOMTEWIFI"
WELCOME = (
    "God Jul onskar Huskvarna tomten !!! Tryck pa knappen for att fa ett kul skamt .."
)
DEFAULT = (
    "När öppnar en småläning sin börs?"
    "................ Då någon vill lägga pengar i den!",
    "Varför ramlar de där ungarna hela tiden?" "................ De är ju trillingar!",
    "Vilket djur mår sämst?" "................ Moskiten.",
    "Var kan man köpa kor billigast i världen?" "................. Korea.",
    "Vad är klockan?" "................. En anordning som visar tiden.",
    "Vad är en groda utan ben?" "................. Hopplös.",
    "Vilket djur är coolast?" "................. Svalan.",
)

FORM = b"""
<form action="/ny" method="POST">
<p>Ange ny vers:</p>
<input type="text" name="vers"  required>
<button type="submit">Submit</button>  
</form>"""

FN = "jokes.txt"

app = web.App(host="0.0.0.0", port=80)


def fix_letters(text):
    _ = {("Å", "Ä"): "A", ("å", "ä"): "a", ("Ö",): "O", ("ö",): "o"}
    for k, v in _.items():
        for l in k:
            text = text.replace(l, v)
    return text


def read_texts():
    print("read text")
    current = DEFAULT
    try:
        with open(FN, "r") as f:
            current = f.read().split("\n")
    except Exception:
        pass
    return current


def write_texts(text_list):
    print("write text")
    with open(FN, "w") as f:
        f.write("\n".join(text_list))


def add_text_to_file(text):
    current = list(read_texts())
    current.append(text)
    write_texts(current)


def erase_text(with_defaults=True):
    print("erase all")
    if with_defaults:
        write_texts(DEFAULT)
    else:
        write_texts(("Hej..",))


@app.route("/")
async def handler(r, w):
    print("GET /")
    # write http headers
    w.write(b"HTTP/1.0 200 OK\r\n")
    w.write(b"Content-Type: text/html; charset=utf-8\r\n")
    w.write(b"\r\n")
    # write page body
    w.write(b"<html><body>")
    w.write("Huskvarna tomtens berättelser<br/><br/><br/>")
    w.write(b"Aktuella historied inlagda:<br/>")
    for _ in read_texts():
        w.write(_.encode() + b"<br/>")
    w.write(b"<br/><br/>")
    w.write(FORM)
    w.write('<br/><a href="/rensa">Lägg in standard list</a>')
    w.write(b'<br/><a href="/tom">Gör en tom lista</a>')
    w.write(b"</body></html>")
    # drain stream buffer
    await w.drain()


@app.route("/rensa")
async def handler(r, w):
    print("GET /")
    # write http headers
    w.write(b"HTTP/1.0 200 OK\r\n")
    w.write(b"Content-Type: text/html; charset=utf-8\r\n")
    w.write(b"\r\n")
    # write page body
    w.write(b"<html><body>")
    w.write(b"Skapar standard lista!!!<br/><br/><br/>")
    w.write(b"<br/><br/>")
    w.write(b'<a href="/">Tillbaka</a>')
    w.write(b"</body></html>")
    # drain stream buffer
    await w.drain()
    erase_text()


@app.route("/tom")
async def handler(r, w):
    print("GET /")
    # write http headers
    w.write(b"HTTP/1.0 200 OK\r\n")
    w.write(b"Content-Type: text/html; charset=utf-8\r\n")
    w.write(b"\r\n")
    # write page body
    w.write(b"<html><body>")
    w.write(b"Rensat bort allt!!!<br/><br/><br/>")
    w.write(b"<br/><br/>")
    w.write(b'<a href="/">Tillbaka</a>')
    w.write(b"</body></html>")
    # drain stream buffer
    await w.drain()
    erase_text(False)


@app.route("/ny", methods=["POST"])
async def handler(r, w):
    print("POST /ny")
    body = await r.read(1024)
    form = web.parse_qs(body.decode())
    vers = form.get("vers")
    # write http headers
    w.write(b"HTTP/1.0 200 OK\r\n")
    w.write(b"Content-Type: text/html; charset=utf-8\r\n")
    w.write(b"\r\n")
    # write page body
    w.write(b"Sparar ned: {}".format(vers))
    w.write(b'<br/><br/><a href="/">Tillbaka</a>')
    add_text_to_file(vers)
    # drain stream buffer
    await w.drain()


class Scroller:
    def __init__(
        self,
        display_controller=None,
        scl=pins["scl"],
        sda=pins["sda"],
        width=128,
        height=32,
    ):
        i2c = I2C(scl=Pin(scl), sda=Pin(sda))
        self.oled = ssd1306.SSD1306_I2C(width, height, i2c)
        self.text_width = 16
        self.t = ""
        self.run = False
        self.display_controller = display_controller

    def clear(self):
        self.oled.fill(0)
        self.oled.show()

    def start(self):
        self.run = True

    def stop(self):
        print("stopping")
        self.run = False

    def add_prefix_padding(self):
        self.t = (" " * self.text_width) + self.t

    def text_length(self, t):
        return self.text_width + len(t)

    async def show_text(self, x=0, y=0):
        self.clear()
        self.oled.text(self.t, x, y)
        await uasyncio.sleep_ms(0)
        self.oled.show()

    def set_text(self, text):
        print(f"text: {text}")
        self.t = text

    def pop_first_letter(self):
        _ = list(self.t)
        if not _:
            return
        _.pop(0)
        self.set_text("".join(_))

    async def scroll_text(self, t, sleep_time=0.2):
        uasyncio.sleep_ms(500)
        self.start()
        fixed_text = fix_letters(t)
        self.set_text(fixed_text)
        self.add_prefix_padding()
        for i in range(self.text_length(t) + 1):
            if not self.run:
                break
            await self.show_text()
            uasyncio.sleep(sleep_time)
            self.pop_first_letter()
            if not self.run:
                break
            if self.display_controller:
                print(self.display_controller.button_pressed())
                if self.display_controller.button_pressed():
                    break
        self.stop()
        self.clear()


class DisplayController:
    def __init__(self, pin=pins["button"]):
        print("start display controller")
        self.scroller = Scroller(self)
        self.button = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.loop = uasyncio.get_event_loop()
        self.led = Pin(pins["led"], Pin.OUT)

    async def start_blink(self):
        while True and self.run:
            await uasyncio.sleep(1)
            self.led.value(not self.led.value())

    async def start_ap(self):
        if WOKWI:
            sta_if = network.WLAN(network.STA_IF)
            sta_if.active(True)
            sta_if.connect("Wokwi-GUEST", "")
            while not sta_if.isconnected():
                print(".", end="")
                uasyncio.sleep_ms(200)
            print(" Connected!")
        else:
            ap = network.WLAN(network.AP_IF)
            ap.active(True)
            ap.config(essid=SSID)
            while ap.active() == False:
                uasyncio.sleep_ms(200)
                pass
            print("Connection successful")
            print(ap.ifconfig())

    async def start(self):
        self.run = True
        uasyncio.create_task(self.start_ap())
        uasyncio.create_task(self.start_blink())
        uasyncio.create_task(self.scroller.scroll_text(WELCOME))
        await self.check_button()

    def stop(self):
        self.run = False

    async def check_button(self):
        print("starting check button in background")
        while self.run:
            if self.button_pressed():
                print("button pressed")
                await self.debounce()
                # await self.display_new_text()
                uasyncio.create_task(self.display_new_text())
            await uasyncio.sleep_ms(100)

    async def debounce(self, max_count=10, ms_between=50):
        print("starting debounce")
        counter = 0
        last_state = self.button_pressed()
        fetched_states = []
        while counter < max_count and len(set(fetched_states)) > 1:
            counter += 1
            fetched_states.append(self.button_pressed())
            await uasyncio.sleep_ms(ms_between)
        print("debounce complete")

    def button_pressed(self):
        return not self.button.value()

    async def display_new_text(self, *args):
        self.scroller.stop()
        r = random.randint(0, len(read_texts()) - 1)
        print(r)
        try:
            uasyncio.create_task(self.scroller.scroll_text(read_texts()[r]))
        except IndexError as e:
            print(e)


def set_global_exception():
    def _handle_exception(loop, context):
        import sys

        sys.print_exception(context["exception"])
        sys.exit()

    loop = uasyncio.get_event_loop()
    loop.set_exception_handler(_handle_exception)


async def amain():
    print("start main")
    current = read_texts()
    count = len(current)
    print(f"Current ones ({count}):")
    print(current)
    loop = uasyncio.get_event_loop()
    set_global_exception()
    loop.create_task(app.serve())
    dc = DisplayController()
    await dc.start()


if __name__ == "__main__":
    try:
        uasyncio.run(amain())
    except OSError as e:
        print("ERROR:", e)
        for _ in range(10):
            p = Pin(2, Pin.OUT)
            p.value(not p.value())
            time.sleep(1)
        raise
