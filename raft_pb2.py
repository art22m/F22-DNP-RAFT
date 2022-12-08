# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: raft.proto
"""Generated protocol buffer code."""
from google.protobuf.internal import builder as _builder
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\nraft.proto\"`\n\x0bVoteRequest\x12\x0c\n\x04term\x18\x01 \x01(\x03\x12\x14\n\x0c\x63\x61ndidate_id\x18\x02 \x01(\x03\x12\x16\n\x0elast_log_index\x18\x03 \x01(\x03\x12\x15\n\rlast_log_term\x18\x04 \x01(\x03\")\n\tVoteReply\x12\x0c\n\x04term\x18\x01 \x01(\x03\x12\x0e\n\x06result\x18\x02 \x01(\x08\"\x87\x01\n\rAppendRequest\x12\x0c\n\x04term\x18\x01 \x01(\x03\x12\x11\n\tleader_id\x18\x02 \x01(\x03\x12\x16\n\x0eprev_log_index\x18\x03 \x01(\x03\x12\x15\n\rprev_log_term\x18\x04 \x01(\x03\x12\x0f\n\x07\x65ntries\x18\x05 \x01(\x03\x12\x15\n\rleader_commit\x18\x06 \x01(\x03\",\n\x0b\x41ppendReply\x12\x0c\n\x04term\x18\x01 \x01(\x03\x12\x0f\n\x07success\x18\x02 \x01(\x08\"4\n\x0eGetLeaderReply\x12\x11\n\tleader_id\x18\x01 \x01(\x03\x12\x0f\n\x07\x61\x64\x64ress\x18\x02 \x01(\t\" \n\x0eSuspendRequest\x12\x0e\n\x06period\x18\x01 \x01(\x03\"(\n\nSetRequest\x12\x0b\n\x03key\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\t\"\x1b\n\x08SetReply\x12\x0f\n\x07success\x18\x01 \x01(\x08\"\x19\n\nGetRequest\x12\x0b\n\x03key\x18\x01 \x01(\t\"*\n\x08GetReply\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\r\n\x05value\x18\x02 \x01(\t\"\x0e\n\x0c\x45mptyMessage2\x92\x02\n\x0bRaftService\x12*\n\x0crequest_vote\x12\x0c.VoteRequest\x1a\n.VoteReply\"\x00\x12\x30\n\x0e\x61ppend_entries\x12\x0e.AppendRequest\x1a\x0c.AppendReply\"\x00\x12#\n\x07set_val\x12\x0b.SetRequest\x1a\t.SetReply\"\x00\x12#\n\x07get_val\x12\x0b.GetRequest\x1a\t.GetReply\"\x00\x12.\n\nget_leader\x12\r.EmptyMessage\x1a\x0f.GetLeaderReply\"\x00\x12+\n\x07suspend\x12\x0f.SuspendRequest\x1a\r.EmptyMessage\"\x00\x62\x06proto3')

_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'raft_pb2', globals())
if _descriptor._USE_C_DESCRIPTORS == False:

  DESCRIPTOR._options = None
  _VOTEREQUEST._serialized_start=14
  _VOTEREQUEST._serialized_end=110
  _VOTEREPLY._serialized_start=112
  _VOTEREPLY._serialized_end=153
  _APPENDREQUEST._serialized_start=156
  _APPENDREQUEST._serialized_end=291
  _APPENDREPLY._serialized_start=293
  _APPENDREPLY._serialized_end=337
  _GETLEADERREPLY._serialized_start=339
  _GETLEADERREPLY._serialized_end=391
  _SUSPENDREQUEST._serialized_start=393
  _SUSPENDREQUEST._serialized_end=425
  _SETREQUEST._serialized_start=427
  _SETREQUEST._serialized_end=467
  _SETREPLY._serialized_start=469
  _SETREPLY._serialized_end=496
  _GETREQUEST._serialized_start=498
  _GETREQUEST._serialized_end=523
  _GETREPLY._serialized_start=525
  _GETREPLY._serialized_end=567
  _EMPTYMESSAGE._serialized_start=569
  _EMPTYMESSAGE._serialized_end=583
  _RAFTSERVICE._serialized_start=586
  _RAFTSERVICE._serialized_end=860
# @@protoc_insertion_point(module_scope)
