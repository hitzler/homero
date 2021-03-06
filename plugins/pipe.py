from util import hook, strip_formatting

# lets work out how we do this
#
# create an empty queue of stuff to output
#   we wanna support multi line commands line bigjab. each time we hit a new
#   command, each thing in the list gets filtered through it
#
# override reply and say functions
#   some plugins dont return what they wanna say, instead they use input.say
#   or input.reply. we should override these functions so we can steal their
#   args and push them into our output queue

# silly lil fifo thing class
class Fifo(object):
  def __init__(self):
    self.q = []

  def push(self, n):
    self.q.append(n)

  def pop(self):
    return self.q.pop(0)

  def empty(self):
    return not (len(self.q) > 0)

  def __iter__(self):
    return self

  def next(self):
    try:
      return self.pop()
    except IndexError,e :
      raise StopIteration()

  def __len__(self):
    return len(self.q)

def split_cmd(cmd):
  func = cmd.split()[0]
  args = cmd[len(func)+1:].strip()
  return func, args

def call(func, func_name, inp, input):
  # mostly copy/pasted from main.py
  args = func._args
  if args:
    if 'db' in args and 'db' not in input:
      input.db = db
    if 'input' in args:
      input.input = input
      input.trigger = func_name
    if 0 in args:
      return func(input.inp, **input)
    else:
      kw = dict((key, input[key]) for key in args if key in input)
      return func(inp, **kw)
  else:
    return func(inp)


@hook.command
def pipe(inp, db=None, input=None, bot=None):
  ".pipe <cmd> | <cmd> etc etc. pipe commands into each other. if the first word after the pipe isnt a command the text gets sent to the next command"
  cmds = inp.split('|')

  output = Fifo()
  nxt = Fifo()

  def f(x):
    nxt.push(x)

  # function overriding
  say = input.say
  reply = input.reply
  input.say = f
  input.reply = f

  for cmd in cmds:
    nxt = Fifo()

    cmd = cmd.strip()

    if cmd[0] == '"' and cmd[-1] == '"':
      cmd = cmd[1:-1]
      output.push(strip_formatting.strip(cmd))
      continue

    func_name, args = split_cmd(cmd)

    # if the first word doesnt map to a func push the whole thing into the queue
    try:
      funcs = [i[0] for i in bot.plugs['command'] if i[1]['name'].startswith(func_name)]
      if len(funcs) > 1:
        funcs = [f.func_name for f in funcs]
        say("did you mean %s or %s?" % (', '.join(funcs[:-1]), funcs[-1]))
        return
      func = funcs[0]
    except IndexError, e:
      output.push(strip_formatting.strip(cmd))
      continue

    args = strip_formatting.strip(args)

    if output.empty():
      output.push(args)

    for line in output:
      res = call(func, func_name, line, input)
      if res:
        nxt.push(res)

    output = nxt

  if len(output) > 20:
    say('woah too many lines (%s)' % len(output))
  else:
    for line in output:
      if isinstance(line, str):
        say(unicode(line, errors='replace'))
      else:
        say(line)
