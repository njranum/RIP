'''  RIP Assignment COSC364 
	 Nicholas Ranum 53147503
	 Erica Shipley 23108940'''


import socket
from select import select
import sys, time, random, collections

HOST = '127.0.0.1'
PERIOD = 30
INFINITY = 16
DEADINTERVAL = 6*PERIOD
PROGRAMTIME = time.time()

''' Class that defines the attributes of a routing table'''
class routingTable(object):
	def __init__(self):
		self.entries = {}
	
	def addEntry(self, entry):
		self.entries[entry[0]] = (entry[1], time.time() - PROGRAMTIME, entry[2])
		
	def updateTable(self, entry, routerID):
		"""Should new entry be added?"""
		dest = entry[0]
		cost = int(entry[1])
		source = entry[2]
		if (dest not in self.entries): # currently no entry for destination
			if (cost < INFINITY):
				self.addEntry(entry)
			return entry
		elif (cost < int(self.entries.get(dest)[0])): # better path than current known path
			self.addEntry(entry)
		elif (source == self.entries[dest][2]) and (cost >= INFINITY):
			if dest != routerID:
				self.addEntry((dest,INFINITY,source))
				print("Recieved cost at infinity")
				return True
		else:
			pass
		return None
	
	def updateTime(self, source):
		for dest,info in self.entries.items():
			if info[2] == source:
				self.entries[dest] = (info[0], time.time() - PROGRAMTIME, info[2])

	def printTable(self):
		ordEntries = collections.OrderedDict(sorted(self.entries.items()))
		print("--------------RIP table entry-----------------")
		for dest, cost in ordEntries.items():
			print(str(dest) + " at cost " + str(cost[0]) + " from " + cost[2] + ". Recived entry at t = " + str(int(cost[1])))
		print("----------------------------------------------")
		return None
	
''' Class that defines the parameters of a router'''
class router(object):
	
	'''initialisation of the router class'''
	def __init__(self, idNo, inputPorts, outputPorts):
		self.table = routingTable()
		self.inputSockets = []
		self.id = idNo
		self.inputs = inputPorts
		self.outs = outputPorts
		self.neighbours = {}
	
	def createSockets(self):
		''' For each input port bind a socket to the port'''
		for port in self.inputs:
			try:
				s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
				s.bind((HOST, int(port)))
				self.inputSockets.append(s)
			except:
				print("Unable to bind socket to port: " + str(port))
				s.close()
				
	def recieveUpdate(self):
		'''Recieves a packet from neighbour'''
		readable, writable, exceptional = select(self.inputSockets, [], [], 6)
		recievedPackets = []
		for ready in readable: # A 'ready' server socket is ready to accept a connection
			
			packet, address = ready.recvfrom(1024)
			
			if address[0] != HOST:
				print("Packet recieved from unknown address")
				return None
			packet = packet.decode(encoding='utf-8')
			recievedPackets.append(packet)

		for packet in recievedPackets:
			self.processPacket(str(packet))
			
		return None
				
	def processPacket(self, packet):
		packet = packet.splitlines()
		
		command = packet[0].split()
		if (command[0] != "Command") or (command[1] != "Response"): # Check command field is set to response
			print(command[0])
			return None
		
		version = packet[1].split()
		if (version[0] != "Version") or (int(version[1]) != 2): # Check version = 2
			print(version[0])
			return None
			
		port = 0
		source = 0
		header = packet[2].split()
		if header[0] == "HEADER": # Check header format
			source = header[1]
			port = header[2]
		
		for i in range(3,len(packet)): # Body of update packet
			entry = packet[i].split()
			if entry[0] != "ENTRY":
				return None # Invalid entry format
			else:
				dest, cost = entry[1], int(entry[2])
				cost += int(self.neighbours[source][0])
				trigger = self.table.updateTable((dest,cost,source), self.id)
				if trigger:
					self.triggeredUpdate()
				if (cost < INFINITY):
					self.table.updateTime(source)

		return None	
	
	def triggeredUpdate(self):
		toDelete = []
		for dest,info in self.table.entries.items():
			if info[0] == INFINITY:
				self.sendUpdate()
				print("deleting entry for: " + dest)
				toDelete.append(dest)
		for dest in toDelete:
			del self.table.entries[dest]	
				
	def initialiseTable(self):
		''' Adds entry for router in the table'''
		self.table.updateTable((self.id,0, '0'), self.id)
		return None
		
	def initialiseNeighbours(self):
		for neighbour in self.outs:
			neighbour = neighbour.split('-')
			port, cost, dest = neighbour[0], neighbour[1], neighbour[2]
			self.neighbours[dest] = (cost,port)
		return None
		
	def sendUpdate(self):
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
		for port in self.outs:
			output = port.split("-")[0]
			message = self.makeMessage(output)
			try:
				sock.sendto(message.encode('utf-8'),(HOST, int(output)))
			except:
				print("Unable to send update on port: " + output)
		return None
		
	def makeMessage(self, port):
		message = "Command Response\n"
		message += "Version 2\n"
		message += "HEADER " + self.id + " " + port + "\n"
		for dest,info in self.table.entries.items():
			source = info[2] # learned from
			cost = info[0]
			''' If the source of a route is the router you are sending
			the update to change the cost to infinity (16)'''
			if (source in self.neighbours) and (source != self.id): 
				if (port == self.neighbours[source][1]):
					cost = INFINITY
			message += "ENTRY " + dest + " " + str(cost) + "\n"
		message = message.rstrip()
		return message
		
	def deadCheck(self):
		cTime = time.time()	- PROGRAMTIME	# Current Time
		toDelete = []
		for entry in self.table.entries:
			if entry != self.id:		# Don't delete the entry for yourself please
				cost, recievedTime, source = self.table.entries[entry]
				difference = cTime - recievedTime
				if ((difference) > DEADINTERVAL):	# Time since update recieved is greater than DEADINTERVAL
					self.table.addEntry((entry,INFINITY,source))
					toDelete.append(entry)
					print("Router through " + str(entry) + " is dead")
		
		if len(toDelete) > 0:
			self.sendUpdate()
			self.table.printTable()
			for dead in toDelete:
				print("Deleting route to " + str(dead))
				del self.table.entries[dead]
		return None
		
def stage1(fileName):
	'''Reads the config file and creates a router based on the config file'''
	print("\nRouter being initialised through configuration file: " + fileName)
	router = makeRouter(fileName)
	ins = ""
	for port in router.inputs:
		ins += port + ", "
	outs = ""
	for port in router.outs:
		outs += port + ", "
	print("\nStage 1 completed.")
	print("Router id: " + str(router.id))
	print("Input ports: " + ins)
	print("Outputs: " + outs)
	return router
	 
def makeRouter(fileName):
	'''open and read the config file'''
	configFile = open(fileName, "r")
	configs = configFile.readlines()
	
	if (len(configs) < 3) or (len(configs) > 4):
		raise Exception("Invalid config file")
	
	'''split the config file up into its parameters'''
	id_line = configs[0].split()
	config_inputs = configs[1].split()
	config_outputs = configs[2].split()
	
	'''checks for the correct config file format'''
	if (id_line[0] != "router-id") or (config_inputs[0] != "input-ports") or (config_outputs[0] != "outputs"):
		raise Exception("Invalid config file")
	
	'''if there is a 4th line with timer values update the period'''
	if len(configs) == 4:
		config_timer = configs[3].split()
		if config_timer[0] != "timer":
			raise Exception("Invalid config file")
		else:
			try:
				PERIOD = int(config_timer[1])
				DEADINTERVAL = PERIOD*6
			except:
				print("Invalid timer value, using default PERIOD = 6")
	
	router_id = id_line[1]
	'''Router id must be between 1 and 64000 (inclusive)'''
	try:
		int(router_id)
	except:
		raise Exception("Router id is invalid")
	if (int(router_id) < 1) or (int(router_id) > 64000):
		raise Exception("Router id is invalid: " + router_id)
		
	'''Input ports must be between 1024 and 36400 (inclusive)
	 and not appear more than once'''
	inputPorts = []
	for port in config_inputs[1:]:
		try:
			port = int(port)
			if (port >= 1024) and (port <= 64000) and (str(port) not in inputPorts):
				inputPorts.append(str(port))
		except:
			print("Input port : " + port + " is invalid and has been excluded")
	'''Input ports must be between 1024 and 36400 (inclusive)
	 and not appear more than once or be in the input port list'''
	outputPorts = []
	for port in config_outputs[1:]:
		portNo, cost, dest = port.split('-')
		try:
			portNo = int(portNo)
			if (portNo >= 1024) and (portNo <= 64000) and (str(portNo) not in inputPorts) and (str(port) not in outputPorts):
				if int(cost) < 16:
					outputPorts.append(str(port))
				else:
					print("Cost to " + str(portNo) + " is INFINITY and output is being excluded")
		except:
			print("Output port: " + str(portNo) + " is invalid and has been excluded")
			
	configFile.close()
	
	'''create new router type and return it'''
	newRouter = router(router_id, inputPorts, outputPorts)
	return newRouter
	  
def stage2(router):
	'''Creates as many UDP ports as there are input ports
	   binds each socket to an input port of the router'''
	router.createSockets()
	ports = ""
	for port in router.inputs:
		ports += port + ", "
	print("\nStage 2 completed: UDP sockets bound to router input ports: " + ports + "\n")
	return None
  
def stage3(router):
	"""Responding to events i.e. 1) send own routing table every x seconds and 
    2) receive routing table of a neighbour whenever there is an update"""
	router.initialiseTable()
	router.initialiseNeighbours()
	pTimer = PERIOD*randomTimer()	# Random timer between 0.8*PERIOD and 1.2*PERIOD
	sTime = time.time()	# Time the inf loop starts at
	router.sendUpdate() # Advertise yourself once you have started up
	print("\nStage 3:\nEntering loop\n")
	while True:
		cTime = time.time()		# Current time
		if ((cTime-sTime) > pTimer): 	# Time to send periodic update
			router.sendUpdate()
			sTime = time.time()
			pTimer = PERIOD*randomTimer()
			router.table.printTable()
		else:		# Check for recieved packets
			router.deadCheck()
			router.recieveUpdate()
	return None
			
def randomTimer():
	stop = 120
	ran = random.randrange(40)
	return (float(stop)-float(ran))/100
		
def main():
	try:
		fileName = sys.argv[1]
		router = stage1(fileName)
		stage2(router)
		stage3(router)
	except(KeyboardInterrupt): 
		print("\nSystem cancelled by operator.")
	

	
main()
