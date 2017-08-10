#
# Copyright (c) 2017, Stephanie Wehner
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
# 3. All advertising materials mentioning features or use of this software
#    must display the following acknowledgement:
#    This product includes software developed by Stephanie Wehner, QuTech.
# 4. Neither the name of the QuTech organization nor the
#    names of its contributors may be used to endorse or promote products
#    derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER ''AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import sys, os, time
sys.path.insert(0, os.environ.get('NETSIM'))

from twisted.spread import pb
from twisted.internet import reactor
from twisted.internet.protocol import Factory, Protocol
from twisted.internet.defer import inlineCallbacks, returnValue, DeferredList, Deferred

from SimulaQron.virtNode.basics import *
from SimulaQron.virtNode.quantum import *
from SimulaQron.general.hostConfig import *
from SimulaQron.virtNode.crudeSimulator import *

from SimulaQron.local.setup import *

from SimulaQron.cqc.backend.cqcHeader import *

#####################################################################################################
#
# CQC Factory
#
# Twisted factory for the CQC protocol
#

class CQCFactory(Factory):
	
	def __init__(self, host, name):
		''' 
		Initialize CQC Factory. 

		lhost	details of the local host (class host)
		'''

		self.host = host	
		self.name = name
		self.virtRoot = None
		self.qReg = None

		# Dictionary that keeps qubit dictorionaries for each application
		self.qubitList = { };

	def buildProtocol(self, addr):
		'''
		Return an instance of CQCProtocol when a connection is made.
		'''
		return CQCProtocol(self)

	def set_virtual_node(self, virtRoot):
		'''
		Set the virtual root allowing connections to the SimulaQron backend.
		'''
		self.virtRoot = virtRoot

	def set_virtual_reg(self, qReg):
		'''
		Set the default register to use on the SimulaQron backend.
		'''
		self.qReg = qReg


#####################################################################################################
#
# CQC Protocol 
#
# Execute the CQC Protocol giving access to the SimulaQron backend via the universal interface.
#

class CQCProtocol(Protocol):

	def __init__(self, factory):

		# CQC Factory, including our connection to the SimulaQron backend
		self.factory = factory;

		# Default application ID, typically one connection per application but we will
		# deliberately NOT check for that since this is the task of higher layers or an OS
		self.app_id = 0;

		# Functions to invoke when receiving a CQC Header of a certain type
		self.messageHandlers = {
			CQC_TP_HELLO : self.handle_hello,
			CQC_TP_COMMAND : self.handle_command,
			CQC_TP_FACTORY : self.handle_factory,
			CQC_TP_GET_TIME : self.handle_time
		}

		# Functions to invoke when receiving a certain command
		self.commandHandlers = {
			CQC_CMD_I : self.cmd_i,
			CQC_CMD_X : self.cmd_x,
			CQC_CMD_Y : self.cmd_y,
			CQC_CMD_Z : self.cmd_z,
			CQC_CMD_T : self.cmd_t,
			CQC_CMD_ROT_X : self.cmd_rotx,
			CQC_CMD_ROT_Y : self.cmd_roty,
			CQC_CMD_ROT_Z : self.cmd_rotz,
			CQC_CMD_CNOT : self.cmd_cnot,
			CQC_CMD_CPHASE : self.cmd_cphase,
			CQC_CMD_MEASURE : self.cmd_measure,
			CQC_CMD_RESET : self.cmd_reset,
			CQC_CMD_SEND : self.cmd_send,
			CQC_CMD_RECV : self.cmd_recv,
			CQC_CMD_EPR : self.cmd_epr,
			CQC_CMD_NEW : self.cmd_new
		}
	

		# Flag to determine whether we already received _all_ of the CQC header
		self.gotCQCHeader = False;

		# Header for which we are currently processing a packet
		self.currHeader = None

		# Buffer received data (which may arrive in chunks)
		self.buf = None

		# Convenience
		self.name = self.factory.name;

		logging.debug("CQC %s: Initialized Protocol",self.name)

	def connectionMade(self):
		pass

	def connectionLost(self, reason):
		pass

	def dataReceived(self, data):
		"""
		Receive data. We will always wait to receive enough data for the header, and then the entire packet first before commencing processing.
		"""

		# Read whatever we received into a buffer	
		if self.buf:
			self.buf = self.buf + data
		else:
			self.buf = data

		# If we don't have the CQC header yet, try and read it in full.
		if not self.gotCQCHeader:
			if len(self.buf) < CQC_HDR_LENGTH:
				# Not enough data for CQC header, return and wait for the rest
				return

			# Got enough data for the CQC Header so read it in
			self.gotCQCHeader = True;
			rawHeader = self.buf[0:CQC_HDR_LENGTH]
			self.currHeader = CQCHeader(rawHeader);
			logging.debug("CQC %s: Read CQC Header: %s", self.name, self.currHeader.printable())

			# Remove the header from the buffer
			self.buf = self.buf[CQC_HDR_LENGTH:len(self.buf)]

		# Check whether we already received all the data
		if len(self.buf) < self.currHeader.length:
			# Still waiting for data
			return

		# We got the header and all the data for this packet. Start processing.
		logging.debug("CQC %s: Processing packet.", self.name)

		# Update our app ID
		self.app_id = self.currHeader.app_id;

		# Invoke the relevant message handler, processing the possibly remaining data
		if self.currHeader.tp in self.messageHandlers: 
			self.messageHandlers[self.currHeader.tp](self.currHeader, self.buf[0:self.currHeader.length])
		else:	
			self._send_back_cqc(header, CQC_ERR_UNSUPP)

		# Reset and await the next packet
		self.gotCQCHeader = False

		# Check if we received data already for the next packet, if so save it
		if self.currHeader.length < len(self.buf):
			self.buf = self.buf[self.currHeader.length:len(self.buf)]
		else:
			self.buf = None

	def get_virt_qubit(self, header, qubit_id):
		"""
		Get reference to the virtual qubit reference in SimulaQron given app and qubit id, if it exists. If not found, send back no qubit error.
		"""
		if not (header.app_id, qubit_id) in self.factory.qubitList:
			logging.debug("CQC %s: Qubit not found",self.name)
			self._send_back_cqc(header, CQC_ERR_NOQUBIT)
			return None

		qubit = self.factory.qubitList[(header.app_id, qubit_id)]
		return qubit.virt


	def _send_back_cqc(self,header, msgType):
		"""
		Return a simple CQC header with the specified type.

		header	 CQC header of the packet we respond to
		msgType  Message type to return
		"""
		hdr = CQCHeader();
		hdr.setVals(CQC_VERSION, msgType, header.app_id);
		msg = hdr.pack();
		self.transport.write(msg)

	def handle_hello(self, header, data):
		"""
		Hello just requires us to return hello - for testing availablility.
		"""
		hdr = CQCHeader();
		hdr.setVals(CQC_VERSION, CQC_TP_HELLO, header.app_id);
		msg = hdr.pack();
		self.transport.write(msg)

	@inlineCallbacks
	def handle_command(self, header, data):
		"""
		Handle incoming command requests. 
		"""

		logging.debug("CQC %s: Received command, length %d", self.name, header.length)
		
		# Run the entire command list, incl. actions after completion which here we will do instantly
		succ = yield self._process_command(header, header.length, data);
		if succ:
			# Send a notification that we are done if successful
			self._send_back_cqc(header, CQC_TP_DONE);
			logging.debug("CQC %s: Command successful, sent done.", self.name)

	@inlineCallbacks	
	def _process_command(self, cqc_header, length, data):
		'''
			Process the commands - called recursively to also process additional command lists.
		'''
		cmdData = data

		# Read in all the commands sent
		l = 0;
		while l < length:
			cmd = CQCCmdHeader(cmdData[l:l+CQC_CMD_HDR_LENGTH]);
			newl = l + CQC_CMD_HDR_LENGTH;
			logging.debug("CQC %s: Read CMD Header: %s", self.name, cmd.printable())

			# Check if this command includes an additional header
			if self.hasXtra(cmd):
				xtra = CQCCmdExtra(cmdData[newl:newl+CQC_CMD_XTRA_LENGTH]);
				newl = newl + CQC_CMD_XTRA_LENGTH;
			else:
				xtra = None;

			# Run this command
			logging.debug("CQC %s: Executing command: %s", self.name, cmd.printable())
			succ = yield self.commandHandlers[cmd.instr](cqc_header, cmd, xtra);
			if not succ:
				return False

			logging.debug("CQC %s: Done command.", self.name)

			# Check if there are additional commands to execute afterwards
			if cmd.action:
				succ = self._process_command(cqc_header, xtra.cmdLength, data[newl:newl+xtra.cmdLength])
				if not succ:
					return False
				newl = newl + xtra.cmdLength;

			l = newl;

		return True

	def hasXtra(self, cmd):
		'''
			Check whether this command includes an extra header with additional information.
		'''
		if cmd.instr == CQC_CMD_RECV:
			return(True);
		if cmd.instr == CQC_CMD_SEND:
			return(True);
		if cmd.instr == CQC_CMD_EPR:
			return(True);
		if cmd.instr == CQC_CMD_CNOT:
			return(True);
		if cmd.instr == CQC_CMD_CPHASE:
			return(True);
		if cmd.action:
			return(True);

		return(False);
		

	def handle_factory(self, header, data):
		pass

	def handle_time(self, header, data):

		# Read the command header to learn the qubit ID
		rawCmdHeader = data[4:4+CQC_CMD_HDR_LENGTH];
		hdr = CQCCmdHeader(rawCmdHeader);

		# Lookup the desired qubit list for application
		qList = self.qDict[header.app_id];
		if not qList:
			# App ID has no qubits
			self._send_back_cqc(header, CQC_ERR_NOQUBIT);
			return;

		# Lookup the desired qubit
		if not qList[hdr.qubit_id]:
			# Specified qubit is unknown	
			send_noqubit(self, header);
			return;

		# Craft reply
		# First send an appropriate CQC Header
		self._send_back_cqc(header, CQC_TP_INF_TIME);

		# Then we send a notify header with the timing details
		notify = CQCNotifyHeader();
		notify.setVals(header.qubit_id, 0, 0, 0, q.timestamp);
		msg = notify.pack();
		self.transport.write(msg)

	def cmd_i(self, cqc_header, cmd, xtra):
		"""
		Do nothing. In reality we would wait a timestep but in SimulaQron we just do nothing.
		"""
		pass

	@inlineCallbacks
	def cmd_x(self, cqc_header, cmd, xtra):
		"""
		Apply X Gate
		"""
		logging.debug("CQC %s: Applying X to App ID %d qubit id %d",self.name,cqc_header.app_id,cmd.qubit_id)
		virt_qubit = self.get_virt_qubit(cqc_header, cmd.qubit_id)
		if not virt_qubit:
			return False

		yield virt_qubit.callRemote("apply_X")
		return True

	@inlineCallbacks
	def cmd_z(self, cqc_header, cmd, xtra):
		"""
		Apply Z Gate
		"""
		logging.debug("CQC %s: Applying Z to App ID %d qubit id %d",self.name,cqc_header.app_id,cmd.qubit_id)
		virt_qubit = self.get_virt_qubit(cqc_header, cmd.qubit_id)
		if not virt_qubit:
			return False

		yield virt_qubit.callRemote("apply_Z")
		return True

	@inlineCallbacks
	def cmd_y(self, cqc_header, cmd, xtra):
		"""
		Apply Y Gate
		"""
		logging.debug("CQC %s: Applying Y to App ID %d qubit id %d",self.name,cqc_header.app_id,cmd.qubit_id)
		virt_qubit = self.get_virt_qubit(cqc_header, cmd.qubit_id)
		if not virt_qubit:
			return False

		yield virt_qubit.callRemote("apply_Y")
		return True

	@inlineCallbacks
	def cmd_t(self, cqc_header, cmd, xtra):
		"""
		Apply T Gate
		"""
		logging.debug("CQC %s: Applying T to App ID %d qubit id %d",self.name,cqc_header.app_id,cmd.qubit_id)
		virt_qubit = self.get_virt_qubit(cqc_header, cmd.qubit_id)
		if not virt_qubit:
			return False

		yield virt_qubit.callRemote("apply_T")
		return True

	@inlineCallbacks
	def cmd_h(self, cqc_header, cmd, xtra):
		"""
		Apply H Gate
		"""
		logging.debug("CQC %s: Applying H to App ID %d qubit id %d",self.name,cqc_header.app_id,cmd.qubit_id)
		virt_qubit = self.get_virt_qubit(cqc_header, cmd.qubit_id)
		if not virt_qubit:
			return False

		yield virt_qubit.callRemote("apply_H")
		return True

	@inlineCallbacks
	def cmd_rotx(self, cqc_header, cmd, xtra):
		"""
		Rotate around x axis
		"""
		pass

	@inlineCallbacks
	def cmd_rotz(self, cqc_header, cmd, xtra):
		'''
			Rotate around z axis
		'''
		pass

	@inlineCallbacks
	def cmd_roty(self, cqc_header, cmd, xtra):
		''' 
			Rotate around y axis
		'''
		pass

	@inlineCallbacks
	def cmd_cnot(self, cqc_header, cmd, xtra):
		"""
		Apply CNOT Gate
		"""
		logging.debug("CQC %s: Applying CNOT to App ID %d qubit id %d",self.name,cqc_header.app_id,cmd.qubit_id)
		control = self.get_virt_qubit(cqc_header, cmd.qubit_id)
		target = self.get_virt_qubit(cqc_header, xtra.qubit_id)
		if not(control) or not(target):
			return False

		yield control.callRemote("cnot_onto",target)
		return True

	@inlineCallbacks
	def cmd_cphase(self, cqc_header, cmd, xtra):
		"""
		Apply CPHASE Gate
		"""
		logging.debug("CQC %s: Applying CPHASE to App ID %d qubit id %d",self.name,cqc_header.app_id,cmd.qubit_id)
		control = self.get_virt_qubit(cqc_header, cmd.qubit_id)
		target = self.get_virt_qubit(cqc_header, xtra.qubit_id)
		if not(control) or not(target):
			return False

		yield control.callRemote("cphase_onto",target)
		return True
	
	@inlineCallbacks
	def cmd_reset(self, cqc_header, cmd, xtra):
		'''
			Reset Qubit to |0>
		'''
		pass

	@inlineCallbacks
	def cmd_measure(self, cqc_header, cmd, xtra):
		"""
		Measure
		"""
		logging.debug("CQC %s: Measuring App ID %d qubit id %d",self.name,cqc_header.app_id,cmd.qubit_id)
		virt_qubit = self.get_virt_qubit(cqc_header, cmd.qubit_id)
		if not virt_qubit:
			return False

		outcome = yield virt_qubit.callRemote("measure")
		# Send the outcome back as MEASOUT XXX

		return True

	@inlineCallbacks
	def cmd_send(self, cqc_header, cmd, xtra):
		"""
		Send qubit to another node.
		"""
		pass

	@inlineCallbacks
	def cmd_recv(self, cqc_header, cmd, xtra):
		"""
		Receive qubit from another node.
		"""
		pass

	@inlineCallbacks
	def cmd_epr(self, cqc_header, cmd, xtra):
		"""
		Create EPR pair with another node.
		"""
		pass

	@inlineCallbacks
	def cmd_new(self, cqc_header, cmd, xtra):
		"""
		Request a new qubit. Since we don't need it, this python CQC just provides very crude timing information.
		"""

		app_id = cqc_header.app_id
		q_id = cmd.qubit_id
	
		if (app_id,q_id) in self.factory.qubitList:
			logging.debug("CQC %s: Cannot create qubit with the same ID for the same App ID", self.name)
			self._send_back_cqc(cqc_header, CQC_ERR_INUSE)
			return False

		virt = yield self.factory.virtRoot.callRemote("new_qubit_inreg",self.factory.qReg)
		q = CQCQubit(cmd.qubit_id, int(time.time()), virt)
		self.factory.qubitList[(app_id,q_id)] = q
		logging.debug("CQC %s: Requested new qubit (%d,%d)",self.name,app_id, q_id)
		return True


#######################################################################################################
#
# CQC Internal qubit object to translate to the native mode of SimulaQron
#

class CQCQubit:

	def __init__(self, qubit_id = 0, timestamp = 0, virt = 0):
		self.qubit_id = qubit_id;
		self.timestamp = timestamp;
		self.virt = virt;



	
		

