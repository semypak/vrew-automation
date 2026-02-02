# -*- coding: utf-8 -*-
"""
Supabase 인증 및 크레딧 관리 모듈
- 회원가입/로그인
- 크레딧 조회/차감
"""

import requests
import streamlit as st
from datetime import datetime

# Supabase 설정
SUPABASE_URL = "https://qerlctvziyuixxpcxcgw.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFlcmxjdHZ6aXl1aXh4cGN4Y2d3Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk5MjMxMDgsImV4cCI6MjA4NTQ5OTEwOH0.d8jvUpgD1g27sPCGqmSn4-tYMmD1cImFX_LXEAe_G-8"

HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Content-Type": "application/json"
}


def get_auth_headers(access_token):
    """인증된 요청용 헤더"""
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }


def check_youtube_id_exists(youtube_id: str) -> bool:
    """유튜브 멤버십 ID 중복 확인"""
    if not youtube_id:
        return False

    url = f"{SUPABASE_URL}/rest/v1/profiles"
    params = {
        "youtube_membership_id": f"eq.{youtube_id}",
        "select": "id"
    }

    try:
        response = requests.get(url, params=params, headers=HEADERS)
        result = response.json()
        return len(result) > 0
    except:
        return False


def sign_up(email: str, password: str, invite_code: str, youtube_id: str, name: str = "", phone: str = "") -> dict:
    """
    회원가입 (초대 코드, 유튜브 멤버십 ID 필수)
    """
    # 1. 유튜브 멤버십 ID 필수 확인
    if not youtube_id or not youtube_id.strip():
        return {"success": False, "error": "유튜브 멤버십 ID는 필수입니다."}

    # 2. 유튜브 멤버십 ID 중복 확인
    if check_youtube_id_exists(youtube_id):
        return {"success": False, "error": "이미 등록된 유튜브 멤버십 ID입니다."}

    # 3. 초대 코드 확인
    if not verify_invite_code(invite_code):
        return {"success": False, "error": "유효하지 않은 초대 코드입니다."}

    # 4. 회원가입 요청
    url = f"{SUPABASE_URL}/auth/v1/signup"
    data = {
        "email": email,
        "password": password
    }

    try:
        response = requests.post(url, json=data, headers=HEADERS)
        result = response.json()

        print(f"[DEBUG] Signup response: {response.status_code} - {result}")  # 디버그용

        if response.status_code == 200 and result.get("user"):
            # 초대 코드 사용 횟수 증가
            increment_invite_code_usage(invite_code)

            # 프로필 정보 저장 (이름, 전화번호, 유튜브 ID)
            user_id = result["user"]["id"]
            access_token = result.get("access_token")
            update_user_profile(user_id, name, phone, youtube_id, access_token)

            return {
                "success": True,
                "user": result["user"],
                "access_token": result.get("access_token"),
                "message": "회원가입 성공!"
            }
        else:
            # 더 자세한 에러 메시지
            error_msg = result.get("error_description") or result.get("msg") or result.get("error") or f"회원가입 실패 (코드: {response.status_code})"
            print(f"[DEBUG] Signup error: {result}")  # 디버그용
            return {"success": False, "error": error_msg}
    except Exception as e:
        print(f"[DEBUG] Signup exception: {e}")  # 디버그용
        return {"success": False, "error": str(e)}


def update_user_profile(user_id: str, name: str, phone: str, youtube_id: str, access_token: str = None):
    """사용자 프로필 정보 업데이트 (이름, 전화번호, 유튜브 ID)"""
    url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}"
    data = {
        "name": name,
        "phone": phone,
        "youtube_membership_id": youtube_id
    }

    try:
        # 인증 헤더 사용 (RLS 우회)
        if access_token:
            headers = get_auth_headers(access_token)
        else:
            headers = HEADERS
        requests.patch(url, json=data, headers=headers)
    except:
        pass


def sign_in(email: str, password: str) -> dict:
    """
    로그인
    """
    url = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    data = {
        "email": email,
        "password": password
    }

    try:
        response = requests.post(url, json=data, headers=HEADERS)
        result = response.json()

        if response.status_code == 200 and result.get("access_token"):
            return {
                "success": True,
                "access_token": result["access_token"],
                "user": result["user"],
                "message": "로그인 성공!"
            }
        else:
            error_msg = result.get("error_description") or result.get("msg") or "로그인 실패"
            return {"success": False, "error": error_msg}
    except Exception as e:
        return {"success": False, "error": str(e)}


def sign_out():
    """로그아웃"""
    if "access_token" in st.session_state:
        del st.session_state["access_token"]
    if "user" in st.session_state:
        del st.session_state["user"]
    if "credits" in st.session_state:
        del st.session_state["credits"]


def verify_invite_code(code: str) -> bool:
    """초대 코드 유효성 확인"""
    url = f"{SUPABASE_URL}/rest/v1/invite_codes"
    params = {
        "code": f"eq.{code}",
        "is_active": "eq.true",
        "select": "id,code,max_uses,used_count"
    }

    try:
        response = requests.get(url, params=params, headers=HEADERS)
        result = response.json()

        if result and len(result) > 0:
            invite = result[0]
            return invite["used_count"] < invite["max_uses"]
        return False
    except:
        return False


def increment_invite_code_usage(code: str):
    """초대 코드 사용 횟수 증가"""
    # 먼저 현재 값 조회
    url = f"{SUPABASE_URL}/rest/v1/invite_codes"
    params = {"code": f"eq.{code}", "select": "id,used_count"}

    try:
        response = requests.get(url, params=params, headers=HEADERS)
        result = response.json()

        if result and len(result) > 0:
            invite_id = result[0]["id"]
            current_count = result[0]["used_count"]

            # 업데이트
            update_url = f"{SUPABASE_URL}/rest/v1/invite_codes?id=eq.{invite_id}"
            update_data = {"used_count": current_count + 1}
            requests.patch(update_url, json=update_data, headers=HEADERS)
    except:
        pass


def get_user_credits(access_token: str, user_id: str) -> int:
    """사용자 크레딧 조회"""
    url = f"{SUPABASE_URL}/rest/v1/profiles"
    params = {
        "id": f"eq.{user_id}",
        "select": "credits"
    }

    try:
        response = requests.get(url, params=params, headers=get_auth_headers(access_token))
        result = response.json()

        if result and len(result) > 0:
            return result[0].get("credits", 0)
        return 0
    except:
        return 0


def use_credit(access_token: str, user_id: str) -> bool:
    """
    크레딧 1개 사용
    Returns: True if successful, False if no credits left
    """
    current_credits = get_user_credits(access_token, user_id)

    if current_credits <= 0:
        return False

    # 크레딧 차감
    url = f"{SUPABASE_URL}/rest/v1/profiles?id=eq.{user_id}"
    data = {"credits": current_credits - 1}

    try:
        response = requests.patch(url, json=data, headers=get_auth_headers(access_token))

        if response.status_code in [200, 204]:
            # 사용 기록 저장
            log_usage(access_token, user_id, "vrew_generate")
            return True
        return False
    except:
        return False


def log_usage(access_token: str, user_id: str, action: str):
    """사용 기록 저장"""
    url = f"{SUPABASE_URL}/rest/v1/usage_logs"
    data = {
        "user_id": user_id,
        "action": action
    }

    try:
        requests.post(url, json=data, headers=get_auth_headers(access_token))
    except:
        pass


def is_logged_in() -> bool:
    """로그인 상태 확인"""
    return "access_token" in st.session_state and "user" in st.session_state


def get_current_user():
    """현재 로그인된 사용자 정보"""
    if is_logged_in():
        return st.session_state.get("user")
    return None


def render_auth_ui():
    """로그인/회원가입 UI 렌더링"""
    st.markdown("### 🔐 로그인이 필요합니다")

    tab1, tab2 = st.tabs(["로그인", "회원가입"])

    with tab1:
        with st.form("login_form"):
            email = st.text_input("이메일", key="login_email")
            password = st.text_input("비밀번호", type="password", key="login_password")
            submit = st.form_submit_button("로그인", use_container_width=True)

            if submit:
                if not email or not password:
                    st.error("이메일과 비밀번호를 입력해주세요.")
                else:
                    result = sign_in(email, password)
                    if result["success"]:
                        st.session_state["access_token"] = result["access_token"]
                        st.session_state["user"] = result["user"]
                        st.success(result["message"])
                        st.rerun()
                    else:
                        st.error(result["error"])

    with tab2:
        with st.form("signup_form"):
            name = st.text_input("이름 *", key="signup_name")
            phone = st.text_input("전화번호 *", key="signup_phone", help="예: 010-1234-5678")
            email = st.text_input("이메일 *", key="signup_email")
            password = st.text_input("비밀번호 *", type="password", key="signup_password")
            password2 = st.text_input("비밀번호 확인 *", type="password", key="signup_password2")
            youtube_id = st.text_input("유튜브 멤버십 ID *", key="signup_youtube", help="유튜브 채널에서 사용하는 멤버십 ID (필수, 중복 불가)")
            invite_code = st.text_input("초대 코드 *", key="signup_invite")
            submit = st.form_submit_button("회원가입", use_container_width=True)

            if submit:
                if not name or not phone or not email or not password or not invite_code or not youtube_id:
                    st.error("모든 필드를 입력해주세요.")
                elif password != password2:
                    st.error("비밀번호가 일치하지 않습니다.")
                elif len(password) < 6:
                    st.error("비밀번호는 6자 이상이어야 합니다.")
                else:
                    result = sign_up(email, password, invite_code, youtube_id, name, phone)
                    if result["success"]:
                        # 회원가입 성공 시 자동 로그인
                        if result.get("access_token"):
                            st.session_state["access_token"] = result["access_token"]
                            st.session_state["user"] = result["user"]
                            st.success(result["message"])
                            st.rerun()
                        else:
                            # access_token이 없으면 수동 로그인 시도
                            login_result = sign_in(email, password)
                            if login_result["success"]:
                                st.session_state["access_token"] = login_result["access_token"]
                                st.session_state["user"] = login_result["user"]
                                st.success("회원가입 성공!")
                                st.rerun()
                            else:
                                st.success(result["message"] + " 로그인해주세요.")
                    else:
                        st.error(result["error"])
