import imgLingshandaf from '@/static/images/灵山大佛.jpg'
import imgLingshanfangong from '@/static/images/灵山梵宫.jpg'
import imgJiulongguanyu from '@/static/images/九龙灌浴.jpg'
import imgWuyintancheng from '@/static/images/五印坛城.jpg'
import imgBaiziximile from '@/static/images/百子戏弥勒.jpg'
import imgXiangfuchensi from '@/static/images/祥符禅寺.jpg'
import imgAyuwangzhu from '@/static/images/阿育王柱.jpg'
import imgWuzhimen from '@/static/images/五智门.jpg'
import imgFoztan from '@/static/images/佛足坛.jpg'
import imgPutiAvenue from '@/static/images/菩提大道.jpg'
import imgXiangmofudiao from '@/static/images/降魔浮雕.jpg'
import imgNianhuaguangchang from '@/static/images/拈花广场.jpg'
import imgFantianhuahai from '@/static/images/梵天花海.jpg'
import imgWudengHu from '@/static/images/五灯湖.jpg'
import imgLumingGu from '@/static/images/鹿鸣谷.jpg'
import imgManfeilongta from '@/static/images/曼飞龙塔.jpg'
import imgLingshanshengjing from '@/static/images/灵山胜境.jpg'
import imgFojiawenhua from '@/static/images/佛教文化博览馆.jpg'
import imgWujiyizhai from '@/static/images/无尽意斋.jpg'
import imgYoukezhongxin from '@/static/images/游客中心.jpg'
import imgLingshandaZhaoBi from '@/static/images/灵山大照壁.jpg'
import imgXiangyueHuajie from '@/static/images/香月花街.jpg'
import imgNianhuatang from '@/static/images/拈花堂.jpg'

export const DEFAULT_SPOT_IMAGE = imgLingshanshengjing

export const SPOT_IMAGES = {
  '灵山大佛': imgLingshandaf,
  '灵山梵宫': imgLingshanfangong,
  '九龙灌浴': imgJiulongguanyu,
  '五印坛城': imgWuyintancheng,
  '百子戏弥勒': imgBaiziximile,
  '祥符禅寺': imgXiangfuchensi,
  '阿育王柱': imgAyuwangzhu,
  '五智门': imgWuzhimen,
  '佛足坛': imgFoztan,
  '菩提大道': imgPutiAvenue,
  '降魔浮雕': imgXiangmofudiao,
  '拈花广场': imgNianhuaguangchang,
  '梵天花海': imgFantianhuahai,
  '五灯湖': imgWudengHu,
  '鹿鸣谷': imgLumingGu,
  '曼飞龙塔': imgManfeilongta,
  '灵山胜境': imgLingshanshengjing,
  '佛教文化博览馆': imgFojiawenhua,
  '无尽意斋': imgWujiyizhai,
  '灵山胜境游客中心': imgYoukezhongxin,
  '灵山大照壁': imgLingshandaZhaoBi,
  '香月花街': imgXiangyueHuajie,
  '拈花堂': imgNianhuatang
}

export function getSpotImage(name) {
  return SPOT_IMAGES[name] || DEFAULT_SPOT_IMAGE
}
