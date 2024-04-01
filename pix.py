from binascii import crc_hqx
from decimal import Decimal
from pydantic import BaseModel, Field, model_validator, computed_field
from typing import Optional, ClassVar
import abc

class CampoPixBase(BaseModel, abc.ABC):
    id:str = Field(min_length=2,max_length=2,pattern="\d\d")
    nome_emv:str
    tamanho_min:int = Field(ge=1,le=99)
    tamanho_max:int = Field(ge=1,le=99)
    description:Optional[str] = None
    valor:str

    @property
    @abc.abstractmethod
    def default_data(self) -> dict:
        ...

    def default_id(self) -> str:
        return self.default_data['id']

    @computed_field
    @property
    def tamanho(self) -> int:
        return sum(len(str(x)) for x in self.valor)

    @model_validator(mode='after')
    def validar_valor(self):
        if not self.valor:
            raise ValueError(f'Forneça um valor para o campo "valor"')
        if not (self.tamanho_min <= self.tamanho <= self.tamanho_max):
            raise ValueError('O tamanho do campo valor está errado')
        return self

    @model_validator(mode='after')
    def validar_tamanhos(self):
        if self.tamanho_min > self.tamanho_max:
            raise ValueError('O tamanho mínimo do campo valor não pode ser maior do que o tamanho máximo')
        return self

    def __str__(self) -> str:
        return f'{self.id}{str(self.tamanho).zfill(2)}{"".join(str(val) for val in self.valor)}'

    # def __repr__(self) -> str:
    #     return str(self)

class PayloadFormatIndicator(CampoPixBase):
    default_data:dict={'id':'00','nome_emv':'Payload Format Indicator','tamanho_min':2,'tamanho_max':2,'valor':'01','description':"versão do payload QRCPS-MPM, fixo em '01'"}
    def __init__(self, data:dict=default_data):
        super().__init__(**data)

class PointOfInitiationMethod(CampoPixBase):
    default_data:dict={'id':'01','nome_emv':'Point of Initiation Method','tamanho_min':2,'tamanho_max':2,'description':"Se o valor 12 estiver presente, significa que o BR Code só pode ser utilizado uma vez"}
    VALOR_USO_UNICO:ClassVar[str] = '12'
    def __init__(self, valor:str, data=default_data):
        data['valor'] = valor
        super().__init__(**data)

    @classmethod
    def build_default(cls, is_uso_unico:bool, outro_valor_padrao:str='11') -> 'PointOfInitiationMethod':
        valor = cls.VALOR_USO_UNICO if is_uso_unico else outro_valor_padrao
        return PointOfInitiationMethod(valor=valor)

    @property
    def is_uso_unico(self) -> bool:
        return self.valor == self.VALOR_USO_UNICO

class GUIPixPadrao(CampoPixBase):
    default_data:dict={'id':'00','nome_emv':'GUI','tamanho_min':5,'tamanho_max':99,'description':"BR.GOV.BCB.PIX",'valor':"br.gov.bcb.pix"}
    def __init__(self, data:dict=default_data):
        super().__init__(**data)

class ChavePix(CampoPixBase):
    default_data:dict={'id':'01','nome_emv':'Chave PIX','tamanho_min':5,'tamanho_max':99,'description':"Chave PIX"}
    def __init__(self, valor:str, data=default_data):
        data['valor'] = valor
        super().__init__(**data)

    # @model_validator(mode='after')
    # def validar_chave(self):
    #     if len(self.valor) == 11:
    #         if self._validar_cpf(self.valor):
    #             return self
    #         else:
    #             raise ValueError('Erro ao validar o cpf fornecido')
    #     raise ValueError('Não foi possível identificar o tipo de chave pix fornecid (CPF/CNPJ/Aleatória)')

    @staticmethod
    def _validar_cpf(chave:str):
        cpf = [int(char) for char in chave if char.isdigit()]
        if len(cpf) != 11:
            return False
        if cpf == cpf[::-1]:
            return False
        for i in range(9, 11):
            value = sum((cpf[num] * ((i + 1) - num) for num in range(0, i)))
            digit = ((value * 10) % 11) % 10
            if digit != cpf[i]:
                return False
        return True

class MerchantAccountInformationPix(CampoPixBase):
    valor:tuple[GUIPixPadrao,ChavePix]
    default_data:dict={'id':'26','nome_emv':'Merchant Account Information - Pix','tamanho_min':5,'tamanho_max':99}
    def __init__(self, valor:tuple[GUIPixPadrao,ChavePix], data=default_data):
        data['valor'] = valor
        super().__init__(**data)

class MerchantCategoryCode(CampoPixBase):
    default_data:dict={'id':'52','nome_emv':'Merchant Category Code','description':'"0000" ou MCC ISO18245','tamanho_min':4,'tamanho_max':4,'valor':'0000'}
    def __init__(self, data:dict=default_data):
        super().__init__(**data)

class TransactionCurrency(CampoPixBase):
    default_data:dict={'id':'53','nome_emv':'Transaction Currency','description':'"986" - BRL: real brasileiro - ISO4217','tamanho_min':3,'tamanho_max':3,'valor':'986'}
    def __init__(self, data:dict=default_data):
        super().__init__(**data)

class TransactionAmount(CampoPixBase):
    valor_decimal:Decimal
    default_data:dict={'id':'54','nome_emv':'Transaction Amount','description':'valor da transação. Ex.: "0", "1.00", "123.99"','tamanho_min':1,'tamanho_max':13}
    def __init__(self, valor_decimal:Decimal, quantizer:Decimal=Decimal('1.00'), data=default_data):
        data['valor_decimal'] = valor_decimal.quantize(quantizer)
        data['valor'] = str(data['valor_decimal'])
        super().__init__(**data)

class CountryCode(CampoPixBase):
    default_data:dict={'id':'58','nome_emv':'Country Code', 'description':'"BR" - Código de país ISO3166-1 alpha 2','tamanho_min':2,'tamanho_max':2,'valor':'BR'}
    def __init__(self, data:dict=default_data):
        super().__init__(**data)

class MerchantName(CampoPixBase):
    default_data:dict={'id':'59','nome_emv':'Merchant Name','description':'nome do beneficiário/recebedor','tamanho_min':1,'tamanho_max':25}
    def __init__(self, valor:str, data=default_data):
        data['valor'] = valor
        super().__init__(**data)

class MerchantCity(CampoPixBase):
    default_data:dict={'id':'60','nome_emv':'Merchant City','description':'cidade onde é efetuada a transação','tamanho_min':1,'tamanho_max':15}
    def __init__(self, valor:str, data=default_data):
        data['valor'] = valor
        super().__init__(**data)

class PostalCode(CampoPixBase):
    default_data:dict={'id':'61','nome_emv':'Postal Code','description':'CEP da localidade onde é efetuada a transação','tamanho_min':1,'tamanho_max':99}
    def __init__(self, valor:str, data=default_data):
        data['valor'] = valor
        super().__init__(**data)

class ReferenceLabel(CampoPixBase):
    default_data:dict={'id':'05','nome_emv':'Reference Label','description':'ID da transação','tamanho_min':1,'tamanho_max':25}
    VALOR_PADRAO:ClassVar[str] = '***'
    def __init__(self, valor:str, data=default_data):
        data['valor'] = valor
        super().__init__(**data)

    @classmethod
    def build_default(cls, id_da_transacao:str='') -> 'ReferenceLabel':
        valor = id_da_transacao or cls.VALOR_PADRAO
        return ReferenceLabel(valor=valor)

class AdditionalDataFieldTemplate(CampoPixBase):
    valor:tuple[ReferenceLabel]
    default_data:dict={'id':'62','nome_emv':'Additional Data Field Template','description':'','tamanho_min':5,'tamanho_max':29}
    def __init__(self, valor:tuple[ReferenceLabel], data=default_data):
        data['valor'] = valor
        super().__init__(**data)

class CRC16(CampoPixBase):
    default_data:dict={'id':'63','nome_emv':'CRC16','description':'4 nibbles do resultado. Exemplo: 0xAC05 => “AC05”','tamanho_min':4,'tamanho_max':4}
    VALOR_INICIAL:ClassVar[str] = '6304'
    def __init__(self, valor:str, data=default_data):
        data['valor'] = valor
        super().__init__(**data)

    @classmethod
    def build_from_string(cls, pix_string:str) -> 'CRC16':
        return CRC16(valor=cls.crc_compute(pix_string + cls.VALOR_INICIAL))

    @staticmethod
    def crc_compute(hex_string, valor_inicial:int=0xffff):
        msg = bytes(hex_string, 'utf-8')
        crc = crc_hqx(msg, valor_inicial)
        return '{:04X}'.format(crc & valor_inicial)

class PixModel(BaseModel):
    payload_format_indicator:PayloadFormatIndicator = PayloadFormatIndicator()
    point_of_initiation_method:PointOfInitiationMethod
    merchant_account_information_pix:MerchantAccountInformationPix
    merchant_category_code:MerchantCategoryCode = MerchantCategoryCode()
    transaction_currency:TransactionCurrency = TransactionCurrency()
    transaction_amount:TransactionAmount
    country_code:CountryCode = CountryCode()
    merchant_name:MerchantName
    merchant_city:MerchantCity
    postal_code:PostalCode
    additional_data_field_template:AdditionalDataFieldTemplate
    crc16:Optional[CRC16] = None

    @model_validator(mode='after')
    def validar_ids(self):
        campos = self._get_campos()
        ids = [campo.id for campo in campos]
        for id in set(ids):
            if ids.count(id) > 1:
                raise ValueError(f'Há dois ou mais campos com o mesmo id {[campo for campo in filter(lambda x: x.id == id,campos)]}')
        return self

    @classmethod
    def criar_qr_code_estatico(
        cls,
        chave_pix:str,
        valor_pix:Decimal,
        nome_beneficiario_ou_recebedor:str,
        cidade_da_transacao:str,
        cep:str,
        id_da_transacao:str='',
        is_uso_unico:bool=False
    ) -> 'PixModel':
        merchant_account_information_pix = MerchantAccountInformationPix(valor=(GUIPixPadrao(),ChavePix(valor=chave_pix)))
        point_of_initiation_method = PointOfInitiationMethod.build_default(is_uso_unico)
        transaction_amount = TransactionAmount(valor_decimal=valor_pix)
        merchant_name = MerchantName(valor=nome_beneficiario_ou_recebedor)
        merchant_city = MerchantCity(valor=cidade_da_transacao)
        postal_code = PostalCode(valor=cep)
        additional_data_field_template = AdditionalDataFieldTemplate(valor=(ReferenceLabel.build_default(id_da_transacao=id_da_transacao),))
        return PixModel(
            point_of_initiation_method=point_of_initiation_method,
            merchant_account_information_pix=merchant_account_information_pix,
            transaction_amount=transaction_amount,
            merchant_name=merchant_name,
            merchant_city=merchant_city,
            postal_code=postal_code,
            additional_data_field_template=additional_data_field_template
        )

    def _get_campos(self) -> list[CampoPixBase]:
        return [getattr(self,campo) for campo in self.model_fields.keys() if getattr(self,campo) is not None]

    def model_post_init(self,context):
        self.crc16 = CRC16.build_from_string(str(self))
        self.model_validate(self)

    def __str__(self) -> str:
        campos = self._get_campos()
        return "".join(str(campo) for campo in campos if campo is not None)

class Pix:
    def __init__(self, pix_model:PixModel) -> None:
        self.pix_model = pix_model

    @classmethod
    def criar_qr_code_estatico(
        cls,
        chave_pix:str,
        valor_pix:Decimal,
        nome_beneficiario_ou_recebedor:str,
        cidade_da_transacao:str,
        cep:str,
        id_da_transacao:str='',
        is_uso_unico:bool=False
    ) -> 'Pix':
        pix_model = PixModel.criar_qr_code_estatico(chave_pix,valor_pix,nome_beneficiario_ou_recebedor,cidade_da_transacao,cep,id_da_transacao,is_uso_unico)
        return Pix(pix_model=pix_model)

    def get_br_code_string(self) -> str:
        return str(self.pix_model)

    def __str__(self) -> str:
        return self.get_br_code_string()

    def make_qr_code(self):
        ...