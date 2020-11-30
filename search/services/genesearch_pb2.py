# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: services/genesearch.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='services/genesearch.proto',
  package='gcv.services',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\x19services/genesearch.proto\x12\x0cgcv.services\"\"\n\x11GeneSearchRequest\x12\r\n\x05query\x18\x01 \x01(\t\" \n\x0fGeneSearchReply\x12\r\n\x05genes\x18\x01 \x03(\t2X\n\nGeneSearch\x12J\n\x06Search\x12\x1f.gcv.services.GeneSearchRequest\x1a\x1d.gcv.services.GeneSearchReply\"\x00\x62\x06proto3'
)




_GENESEARCHREQUEST = _descriptor.Descriptor(
  name='GeneSearchRequest',
  full_name='gcv.services.GeneSearchRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='query', full_name='gcv.services.GeneSearchRequest.query', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=43,
  serialized_end=77,
)


_GENESEARCHREPLY = _descriptor.Descriptor(
  name='GeneSearchReply',
  full_name='gcv.services.GeneSearchReply',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='genes', full_name='gcv.services.GeneSearchReply.genes', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=79,
  serialized_end=111,
)

DESCRIPTOR.message_types_by_name['GeneSearchRequest'] = _GENESEARCHREQUEST
DESCRIPTOR.message_types_by_name['GeneSearchReply'] = _GENESEARCHREPLY
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

GeneSearchRequest = _reflection.GeneratedProtocolMessageType('GeneSearchRequest', (_message.Message,), {
  'DESCRIPTOR' : _GENESEARCHREQUEST,
  '__module__' : 'services.genesearch_pb2'
  # @@protoc_insertion_point(class_scope:gcv.services.GeneSearchRequest)
  })
_sym_db.RegisterMessage(GeneSearchRequest)

GeneSearchReply = _reflection.GeneratedProtocolMessageType('GeneSearchReply', (_message.Message,), {
  'DESCRIPTOR' : _GENESEARCHREPLY,
  '__module__' : 'services.genesearch_pb2'
  # @@protoc_insertion_point(class_scope:gcv.services.GeneSearchReply)
  })
_sym_db.RegisterMessage(GeneSearchReply)



_GENESEARCH = _descriptor.ServiceDescriptor(
  name='GeneSearch',
  full_name='gcv.services.GeneSearch',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=113,
  serialized_end=201,
  methods=[
  _descriptor.MethodDescriptor(
    name='Search',
    full_name='gcv.services.GeneSearch.Search',
    index=0,
    containing_service=None,
    input_type=_GENESEARCHREQUEST,
    output_type=_GENESEARCHREPLY,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_GENESEARCH)

DESCRIPTOR.services_by_name['GeneSearch'] = _GENESEARCH

# @@protoc_insertion_point(module_scope)
